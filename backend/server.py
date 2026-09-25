#!/usr/bin/env python3
"""
Backend сервер для аудио-анализатора.
Принимает MP3 файлы, конвертирует в PCM, отправляет в Яндекс SpeechKit.
"""

import os
import io
import sys
import json
import tempfile
import subprocess
import logging
import traceback
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Отключаем буферизацию вывода
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Асинхронный endpoint SpeechKit (longRunningRecognize) — рабочий для файлов любого размера
YC_STT_LONGRUNNING_URL = "https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize"
OPERATION_API_URL = "https://operation.api.cloud.yandex.net/operations"
S3_ENDPOINT_URL = "https://storage.yandexcloud.net"

# Регистрируем blueprint для работы с сотрудниками
from api_employees import employees_bp
app.register_blueprint(employees_bp, url_prefix='/api')

# Регистрируем blueprint для работы с Яндекс Облаком (настройки, IAM токен, Object Storage)
from api_yandex_cloud import yandex_cloud_bp
app.register_blueprint(yandex_cloud_bp, url_prefix='/api')


def analyze_audio(input_path: str) -> dict:
    """Анализ аудиофайла"""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(input_path)
        return {
            'duration_sec': round(len(audio) / 1000, 1),
            'sample_rate': audio.frame_rate,
            'channels': audio.channels,
            'rms_dbfs': round(audio.dBFS, 1) if audio.dBFS != float('-inf') else -96.0,
        }
    except Exception as e:
        return {'error': str(e)}


# ==================== ЯНДЕКС ОБЛАКО: Object Storage + SpeechKit v2 (uri) ====================


def _get_yc_settings_or_none():
    """Настройки Яндекс Облака из БД или None."""
    try:
        from repositories import YandexCloudSettingsRepository
        return YandexCloudSettingsRepository.get_settings()
    except Exception as e:
        logger.warning(f"[YC] Не удалось прочитать настройки из БД: {e}")
        return None


def _detect_sample_rate(file_path: str) -> int:
    """Определяет частоту дискретизации MP3 (по умолчанию 48000)."""
    try:
        from pydub import AudioSegment
        sr = AudioSegment.from_file(file_path).frame_rate
        if sr:
            return int(sr)
    except Exception:
        pass
    try:
        res = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a:0',
             '-show_entries', 'stream=sample_rate', '-of', 'csv=p=0', file_path],
            capture_output=True, text=True, timeout=30)
        out = res.stdout.strip()
        if out.isdigit():
            return int(out)
    except Exception:
        pass
    return 48000


def _detect_channels(file_path: str) -> int:
    """Определяет реальное количество каналов в аудиофайле (1 — моно, 2 — стерео)."""
    try:
        from pydub import AudioSegment
        ch = AudioSegment.from_file(file_path).channels
        if ch in (1, 2):
            return int(ch)
    except Exception:
        pass
    try:
        res = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a:0',
             '-show_entries', 'stream=channels', '-of', 'csv=p=0', file_path],
            capture_output=True, text=True, timeout=30)
        out = res.stdout.strip()
        if out.isdigit() and int(out) in (1, 2):
            return int(out)
    except Exception:
        pass
    return 1


def upload_to_object_storage(local_path: str, object_key: str, settings) -> str:
    """Загружает файл в Object Storage (S3-совместимо) и возвращает публичный uri."""
    import boto3

    if not settings.access_key_id or not settings.secret_access_key:
        raise ValueError('Не заданы S3 ключи (Access Key ID / Secret Access Key) в настройках Яндекс Облака')
    if not settings.bucket_name:
        raise ValueError('Не задано имя бакета в настройках Яндекс Облака')

    s3 = boto3.session.Session().client(
        service_name='s3',
        endpoint_url=S3_ENDPOINT_URL,
        region_name='ru-central1',
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key,
    )
    s3.upload_file(Filename=local_path, Bucket=settings.bucket_name, Key=object_key)
    uri = f"{S3_ENDPOINT_URL}/{settings.bucket_name}/{object_key}"
    logger.info(f"[YC] Файл загружен в Object Storage: {uri}")
    return uri


def recognize_via_storage_uri(audio_uri: str, api_key: str, folder_id: str,
                              encoding: str = 'MP3', sample_rate: int = 48000,
                              language: str = 'ru-RU', model: str = 'general',
                              channels: int = 1,
                              poll_interval: int = 5, max_wait_sec: int = 3600,
                              return_segments: bool = False):
    """
    Асинхронное распознавание SpeechKit v2 по ссылке на файл в Object Storage.
    (рабочая схема):
      1) POST transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize
         с config.specification.{audioEncoding,sampleRateHertz,languageCode,model} и audio.uri
      2) опрос operation.api.cloud.yandex.net/operations/{id} до done=true
      3) склейка текста из chunks[].alternatives[0].text

    Если return_segments=True — дополнительно возвращает список сегментов
    с таймкодами (startTime/endTime/text/words), как в полном пайплайне
    (rawResults=True). Иначе возвращается только строка текста.
    """
    import time

    headers = {'Authorization': f'Api-Key {api_key}', 'Content-Type': 'application/json'}
    body = {
        'folderId': folder_id,
        'config': {
            'specification': {
                'languageCode': language,
                'model': model,
                'profanityFilter': False,
                'audioEncoding': encoding,
                'sampleRateHertz': sample_rate,
                'audioChannelCount': channels,   # реальное число каналов файла (1 — моно, 2 — стерео)
                'rawResults': bool(return_segments),  # таймкоды + слова — для расшифровки
            }
        },
        'audio': {'uri': audio_uri},
    }

    resp = requests.post(YC_STT_LONGRUNNING_URL, headers=headers, json=body, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(
            f'SpeechKit longRunningRecognize ошибка {resp.status_code}: {resp.text[:500]}\n'
            f'request-id: {resp.headers.get("x-request-id", "-")}')
    op_id = resp.json()['id']
    logger.info(f"[YC] Операция распознавания создана: {op_id}")

    op_url = f"https://operation.api.cloud.yandex.net/operations/{op_id}"
    waited = 0
    while True:
        op = requests.get(op_url, headers=headers, timeout=30).json()
        if op.get('done'):
            break
        waited += poll_interval
        if waited > max_wait_sec:
            raise TimeoutError(f'Распознавание не завершилось за {max_wait_sec} сек (operation {op_id})')
        logger.info(f"[YC] ...распознаётся, ждём {poll_interval} сек (прошло {waited} сек)")
        time.sleep(poll_interval)

    if 'error' in op:
        raise RuntimeError(f"SpeechKit вернул ошибку операции: {op['error']}")

    response = op.get('response', {})
    chunks = response.get('chunks', [])
    text = ' '.join(
        chunk.get('alternatives', [{}])[0].get('text', '')
        for chunk in chunks
    ).strip()
    logger.info(f"[YC] Распознано {len(text)} символов (async v2 via Object Storage)")

    if not return_segments:
        return text

    # Сегменты с таймкодами (как в полном пайплайне: startTime/endTime/text/words)
    segments = []
    for chunk in chunks:
        alt = (chunk.get('alternatives') or [{}])[0]
        segments.append({
            'startTime': chunk.get('startTime'),
            'endTime': chunk.get('endTime'),
            'text': alt.get('text', ''),
            'words': alt.get('words', []),
        })
    return text, segments


def recognize_speechkit_v2(tmp_path: str, original_filename: str,
                          api_key: str, folder_id: str, settings,
                          language: str = 'ru-RU', model: str = 'general',
                          return_segments: bool = False):
    """
    Распознавание строго по рабочей схеме (пример пользователя):
      1) загрузка файла в Object Storage (boto3, S3-ключи сервисного аккаунта);
      2) POST transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize
         с audio.uri и config.specification.*;
      3) опрос operations/{id} до done=true;
      4) склейка текста из chunks[].alternatives[0].text.
    Других путей распознавания нет — все обязательные настройки берутся
    из вкладки "Яндекс Облако" (БД).
    """
    if not settings or not settings.access_key_id or not settings.secret_access_key or not settings.bucket_name:
        raise ValueError(
            'Object Storage не настроен. Заполните и сохраните во вкладке "Яндекс Облако": '
            'имя бакета, Access Key ID и Secret Access Key.'
        )
    if not folder_id:
        raise ValueError('Не задан Folder ID. Сохраните его во вкладке "Яндекс Облако".')

    from audio_preparation import first_channel_pcm
    from uuid import uuid4
    with first_channel_pcm(tmp_path) as (mono_path, info):
        logger.info("[YC] Канал 1 из %s, PCM 16 кГц mono", info['source_channels'])
        object_key = f"audio-uploads/{uuid4().hex}-channel-1.pcm"
        audio_uri = upload_to_object_storage(mono_path, object_key, settings)
        return recognize_via_storage_uri(
            audio_uri=audio_uri, api_key=api_key, folder_id=folder_id,
            encoding=info['encoding'], sample_rate=info['sample_rate'],
            language=language, model=model, channels=1,
            return_segments=return_segments)



def process_text_with_yandexgpt(raw_text, api_key, folder_id, prompt=None,
                                model='yandexgpt', temperature=0.1,
                                max_output_tokens=4000, employee_id=None, with_client=False):
    """Разбор расшифровки в список заказа.

    По умолчанию (ORDER_PARSER=rules) при выбранном филиале разбор идёт без
    облака: количества по словам («кило двести» = 1.2), кандидаты из справочника
    филиала и проверки в коде (order_pipeline.py). Сомнительная строка не
    подтверждается, а остаётся с needs_review=true и причиной.
    Без выбранного филиала — ошибка «выберите филиал» (YandexGPT не вызывается).
    ORDER_PARSER=llm — прежний платный разбор через YandexGPT.
    with_client=True — вернуть {'order_items', 'client'} (клиент только в локальном разборе).
    Название функции сохранено для совместимости маршрутов и тестов.
    """
    from order_parser import extract_order
    if os.environ.get('ORDER_PARSER', 'rules').lower() != 'llm':
        parsed = parse_for_branch(raw_text, employee_id)
        return parsed if with_client else parsed['order_items']
    catalog = []
    if employee_id:
        from branch_data import load_catalog
        from repositories import EmployeeRepository
        if not EmployeeRepository.get_by_id(employee_id):
            raise ValueError('Выбранный филиал не найден')
        catalog = load_catalog(employee_id)
    items = extract_order(raw_text, api_key, folder_id, prompt, model,
                          temperature, max_output_tokens, catalog)
    return {'order_items': items, 'client': None} if with_client else items


def _items_and_client(parsed):
    return (parsed['order_items'], parsed.get('client')) if isinstance(parsed, dict) else (parsed, None)


def parse_for_branch(raw_text, employee_id):
    """Local parse of one transcript by the branch catalog: order lines + client."""
    if not employee_id:
        raise ValueError('Выберите филиал: заказ разбирается по его справочнику номенклатуры')
    from branch_data import load_branch
    from order_merging import parse_messages
    branch = load_branch(employee_id)
    if not branch['catalog']:
        raise ValueError('В справочнике филиала нет номенклатуры: импортируйте её')
    settings = dict(branch['settings'], merge_messages=False)
    order = parse_messages([{'id': '1', 'text': raw_text}], branch['catalog'], branch['clients'],
                           branch['dictionary'], settings)[0]
    return {'order_items': order['order_items'], 'client': order['client']}


@app.route('/api/process-orders', methods=['POST'])
def process_orders():
    """Несколько расшифровок филиала -> заказы; подряд идущие голосовые одного
    клиента склеиваются в один заказ (опция филиала merge_messages).

    Вход JSON: {"employee_id": "...", "messages": [{"id", "file_name", "text", "last_modified"}]}
    Выход JSON: {"orders": [{message_ids, file_names, merged, merge_reasons, text, client, order_items}]}
    """
    try:
        payload = request.json or {}
        messages = payload.get('messages')
        if not isinstance(messages, list) or not messages:
            return jsonify({'error': 'Не переданы расшифровки (поле "messages")'}), 400
        employee_id = payload.get('employee_id')
        if not employee_id:
            return jsonify({'error': 'Выберите филиал: заказ разбирается по его справочнику номенклатуры'}), 400
        from branch_data import load_branch
        from order_merging import parse_messages
        branch = load_branch(employee_id)
        if not branch['catalog']:
            return jsonify({'error': 'В справочнике филиала нет номенклатуры: импортируйте её'}), 400
        orders = parse_messages([m for m in messages if isinstance(m, dict)], branch['catalog'],
                                branch['clients'], branch['dictionary'], branch['settings'])
        return jsonify({'orders': orders})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/process-order', methods=['POST'])
def process_order_api():
    return process_order()


@app.route('/process-order', methods=['POST'])
def process_order():
    """
    Разбор готового текста расшифровки в список заказа через YandexGPT.
    Промт и модель берутся из настроек Яндекс Облака (БД); можно переопределить в теле запроса.

    Вход JSON: {"text": "...", "employee_id": "(опц.)", "prompt": "(опц.)", "model": "(опц.)"}
    Выход JSON: {"order_items": [...], "model": "..."}
    """
    print("\n" + "=" * 70)
    print("🧠 [PROCESS-ORDER] Разбор расшифровки в список заказа")
    print("=" * 70)
    try:
        payload = request.json or {}
        text = (payload.get('text') or '').strip()
        if not text:
            return jsonify({'error': 'Не передан текст расшифровки (поле "text")'}), 400

        yc_settings = _get_yc_settings_or_none()
        api_key = yc_settings.api_key if yc_settings else None
        folder_id = (payload.get('folderId') or (yc_settings.folder_id if yc_settings else ''))
        prompt = payload.get('prompt') or (yc_settings.order_prompt if yc_settings else None)
        model = payload.get('model') or (yc_settings.yandex_model if yc_settings else None) or 'yandexgpt'

        items, client = _items_and_client(process_text_with_yandexgpt(
            text, api_key or '', folder_id or '', prompt=prompt, model=model,
            employee_id=payload.get('employee_id'), with_client=True))

        print(f"✅ [PROCESS-ORDER] Позиций: {len(items)}")
        return jsonify({'order_items': items, 'client': client, 'model': model})
    except Exception as e:
        print(f"❌ [PROCESS-ORDER] ОШИБКА: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_api():
    """Проверка работоспособности (через /api — фронтенд ходит в Docker-сети только через прокси Vite)"""
    return health()


@app.route('/health', methods=['GET'])
def health():
    """Проверка работоспособности"""
    print("✅ [HEALTH] Запрос проверки работоспособности")
    return jsonify({
        'status': 'ok',
        'service': 'audio-analyzer-backend',
        'version': '1.0.0',
    })


@app.route('/api/recognize', methods=['POST'])
def recognize_api():
    return recognize()


@app.route('/recognize', methods=['POST'])
def recognize():
    """Распознавание речи с опциональным использованием словаря сотрудника"""
    print("\n" + "="*70)
    print("🎤 [RECOGNIZE] Начало распознавания речи")
    print("="*70)
    
    if 'file' not in request.files:
        print("❌ [RECOGNIZE] Файл не предоставлен")
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    api_key = request.form.get('api_key', '')
    folder_id = request.form.get('folder_id', '')
    language = request.form.get('language', 'ru-RU')
    model = request.form.get('model', 'general')
    employee_id = request.form.get('employee_id', '')  # ID сотрудника для словаря

    print(f"✅ [RECOGNIZE] Получен файл: {file.filename}")
    print(f"   Язык: {language}, Модель: {model}")
    if employee_id:
        print(f"   Сотрудник: {employee_id} (используем словарь)")
    
    # API-ключ можно не передавать — возьмём из настроек Яндекс Облака (БД)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        print(f"💾 [RECOGNIZE] Файл сохранён: {tmp_path}")
        
        print("🔍 [RECOGNIZE] Анализируем аудио...")
        audio_info = analyze_audio(tmp_path)
        print(f"✅ [RECOGNIZE] Анализ завершён: {audio_info}")
        
        # Определяем размер файла
        file_size = os.path.getsize(tmp_path)
        print(f"📏 [RECOGNIZE] Размер файла: {file_size / 1024 / 1024:.2f} МБ")
        
        engine = (request.form.get('engine') or os.environ.get('STT_ENGINE', 'speechkit')).lower()
        segments = []
        if engine == 'gigaam':
            # Отдельный локальный сервис: аудио не покидает Docker-сеть, ключи не нужны.
            import gigaam_client
            print(f"🖥️  [RECOGNIZE] Локальный сервис GigaAM ({gigaam_client.model_name()})")
            text, segments = gigaam_client.transcribe(tmp_path)
        else:
            engine = 'speechkit'
            # Object Storage + SpeechKit v2 (uri)
            yc_settings = _get_yc_settings_or_none()

            # API-ключ: из формы, иначе из настроек ЯО в БД
            if not api_key and yc_settings and yc_settings.api_key:
                api_key = yc_settings.api_key
                print("🔑 [RECOGNIZE] Используем API-ключ сервисного аккаунта из настроек Яндекс Облака (БД)")

            # Folder ID: из формы, иначе из настроек ЯО в БД
            if not folder_id and yc_settings and yc_settings.folder_id:
                folder_id = yc_settings.folder_id

            if not api_key:
                return jsonify({'error': 'api_key is required. Укажите API-ключ или сохраните его во вкладке "Яндекс Облако".'}), 400

            stt_result = recognize_speechkit_v2(
                tmp_path=tmp_path,
                original_filename=file.filename,
                api_key=api_key,
                folder_id=folder_id,
                settings=yc_settings,
                language=language,
                model=model,
                return_segments=True,   # текст + сегменты с таймкодами (расшифровка)
            )
            if isinstance(stt_result, tuple):
                text, segments = stt_result
            else:
                text = stt_result
        result = {'result': text}

        print(f"✅ [RECOGNIZE] Распознано: {len(text)} символов")
        print(f"   Текст: {text[:100]}..." if len(text) > 100 else f"   Текст: {text}")

        # Разбор расшифровки в список заказа через YandexGPT (если запрошен фронтом)
        process_llm = request.form.get('process_llm', '').lower() in ('1', 'true', 'yes')
        order_items = None
        client = None
        llm_error = None
        if process_llm and text:
            print("\n🧠 [RECOGNIZE] Разбираю расшифровку в список заказа...")
            try:
                if engine == 'gigaam':
                    yc_settings = None
                llm_prompt = request.form.get('prompt', '') or (yc_settings.order_prompt if yc_settings else None)
                llm_model = request.form.get('llm_model', '') or (yc_settings.yandex_model if yc_settings else None) or 'yandexgpt'
                order_items, client = _items_and_client(process_text_with_yandexgpt(
                    text, api_key, folder_id, prompt=llm_prompt, model=llm_model,
                    employee_id=employee_id, with_client=True))
                print(f"✅ [RECOGNIZE] Позиций заказа: {len(order_items)}")
            except Exception as llm_exc:
                llm_error = str(llm_exc)
                print(f"⚠️  [RECOGNIZE] Ошибка разбора заказа: {llm_exc}")

        print("="*70)
        print("✅ [RECOGNIZE] Возвращаем результат")
        print("="*70 + "\n")
        
        return jsonify({
            'text': text,
            'segments_with_timings': segments,   # расшифровка с таймкодами (SpeechKit rawResults)
            'confidence': result.get('confidence', 0),
            'audio_info': audio_info,
            'raw_response': result,
            'parsed_order': None,  # устаревшее поле; позиции теперь в order_items
            'order_items': order_items,
            'client': client,
            'llm_error': llm_error,
            'engine': engine,
        })

    except Exception as e:
        print(f"\n❌ [RECOGNIZE] ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        print("="*70 + "\n")
        return jsonify({'error': str(e)}), 500

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                print(f"🗑️  [RECOGNIZE] Временный файл удалён")
            except:
                pass


@app.route('/api/analyze', methods=['POST'])
def analyze_api():
    return analyze()


@app.route('/analyze', methods=['POST'])
def analyze():
    """Только анализ файла без распознавания"""
    print("\n" + "="*70)
    print("🔍 [ANALYZE AUDIO] Начало анализа аудио")
    print("="*70)
    
    if 'file' not in request.files:
        print("❌ [ANALYZE AUDIO] Файл не предоставлен")
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    print(f"✅ [ANALYZE AUDIO] Получен файл: {file.filename}")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        print(f"💾 [ANALYZE AUDIO] Файл сохранён: {tmp_path}")
        
        print("🔍 [ANALYZE AUDIO] Анализируем...")
        info = analyze_audio(tmp_path)
        info['file_name'] = file.filename
        info['file_size'] = os.path.getsize(tmp_path)
        
        print(f"✅ [ANALYZE AUDIO] Анализ завершён: {info}")
        print("="*70 + "\n")
        
        return jsonify(info)
    except Exception as e:
        print(f"\n❌ [ANALYZE AUDIO] ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        print("="*70 + "\n")
        return jsonify({'error': str(e)}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                print(f"🗑️  [ANALYZE AUDIO] Временный файл удалён")
            except:
                pass


@app.route('/api/analyze-xlsx', methods=['POST'])
def analyze_xlsx_api():
    return analyze_xlsx()


@app.route('/analyze-xlsx', methods=['POST'])
def analyze_xlsx():
    """
    Анализ XLSX файла — показывает структуру данных.
    
    Принимает:
        - file: XLSX файл
        
    Возвращает:
        - Структуру файла (листы, колонки, типы данных, примеры)
    """
    logger.info("="*70)
    logger.info("📊 [XLSX ANALYZE] Начало анализа файла")
    logger.info("="*70)
    
    if 'file' not in request.files:
        logger.error("❌ [XLSX ANALYZE] Файл не предоставлен в запросе")
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    logger.info(f"✅ [XLSX ANALYZE] Получен файл: {file.filename}")
    logger.info(f"   Размер: {file.content_length} байт" if file.content_length else "   Размер: неизвестен")
    
    # Проверяем расширение
    if not file.filename.lower().endswith('.xlsx'):
        logger.error(f"❌ [XLSX ANALYZE] Неправильное расширение: {file.filename}")
        return jsonify({'error': 'Файл должен быть .xlsx'}), 400

    tmp_path = None
    try:
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        logger.info(f"💾 [XLSX ANALYZE] Файл сохранён: {tmp_path}")
        
        # Импортируем анализатор
        logger.info("📦 [XLSX ANALYZE] Импортируем модуль analyze_xlsx...")
        try:
            from analyze_xlsx import analyze_xlsx as analyze_file
            logger.info("✅ [XLSX ANALYZE] Модуль успешно импортирован")
        except ImportError as e:
            logger.error(f"❌ [XLSX ANALYZE] Ошибка импорта модуля: {e}")
            return jsonify({'error': f'Ошибка импорта модуля: {str(e)}'}), 500
        
        # Анализируем файл
        logger.info("🔍 [XLSX ANALYZE] Начинаем анализ файла...")
        result = analyze_file(tmp_path)
        
        logger.info(f"✅ [XLSX ANALYZE] Анализ завершён успешно")
        logger.info(f"   Найдено листов: {len(result.get('sheets', []))}")
        
        for idx, sheet in enumerate(result.get('sheets', []), 1):
            logger.info(f"   Лист {idx}: {sheet.get('name')} ({sheet.get('max_row')} строк × {sheet.get('max_column')} колонок)")
        
        logger.info("="*70)
        logger.info("✅ [XLSX ANALYZE] Возвращаем результат клиенту")
        logger.info("="*70)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"\n❌ [XLSX ANALYZE] КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
        logger.error("="*70)
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                logger.info(f"🗑️  [XLSX ANALYZE] Временный файл удалён: {tmp_path}")
            except Exception as e:
                logger.warning(f"⚠️  [XLSX ANALYZE] Не удалось удалить временный файл: {e}")


# ==================== ЭНДПОИНТЫ ДЛЯ СОТРУДНИКОВ ====================

@app.route('/api/employees', methods=['GET'])
def list_employees_api():
    return list_employees()


@app.route('/employees', methods=['GET'])
def list_employees():
    """Получить список всех сотрудников"""
    logger.info("📋 [EMPLOYEES] Запрос списка сотрудников")
    
    try:
        from models import EmployeeManager
        manager = EmployeeManager()
        manager.load_all()
        
        employees = manager.list_employees()
        
        result = []
        for emp in employees:
            result.append({
                'id': emp.id,
                'name': emp.name,
                'email': emp.email,
                'phone': emp.phone,
                'position': emp.position,
                'nomenclature_count': len([n for n in emp.nomenclature if n.import_status == 'success']),
                'clients_count': len([c for c in emp.clients if c.import_status == 'success']),
                'created_at': emp.created_at,
            })
        
        logger.info(f"✅ [EMPLOYEES] Найдено сотрудников: {len(result)}")
        return jsonify({'employees': result})
    
    except Exception as e:
        logger.error(f"❌ [EMPLOYEES] Ошибка: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/employees/<employee_id>', methods=['GET'])
def get_employee_api(employee_id):
    return get_employee(employee_id)


@app.route('/employees/<employee_id>', methods=['GET'])
def get_employee(employee_id):
    """Получить информацию о сотруднике"""
    logger.info(f"👤 [EMPLOYEE] Запрос сотрудника: {employee_id}")
    
    try:
        from models import EmployeeManager
        manager = EmployeeManager()
        manager.load_all()
        
        employee = manager.get_employee(employee_id)
        if not employee:
            logger.warning(f"⚠️  [EMPLOYEE] Сотрудник не найден: {employee_id}")
            return jsonify({'error': 'Employee not found'}), 404
        
        logger.info(f"✅ [EMPLOYEE] Сотрудник найден: {employee.name}")
        return jsonify(employee.to_dict())
    
    except Exception as e:
        logger.error(f"❌ [EMPLOYEE] Ошибка: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/employees/<employee_id>/nomenclature', methods=['GET'])
def get_employee_nomenclature_api(employee_id):
    return get_employee_nomenclature(employee_id)


@app.route('/employees/<employee_id>/nomenclature', methods=['GET'])
def get_employee_nomenclature(employee_id):
    """Получить номенклатуру сотрудника"""
    logger.info(f"📦 [NOMENCLATURE] Запрос номенклатуры сотрудника: {employee_id}")
    
    try:
        from models import EmployeeManager
        manager = EmployeeManager()
        manager.load_all()
        
        employee = manager.get_employee(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        nomenclature = [n.to_dict() for n in employee.nomenclature if n.import_status == 'success']
        
        logger.info(f"✅ [NOMENCLATURE] Найдено записей: {len(nomenclature)}")
        return jsonify({'nomenclature': nomenclature})
    
    except Exception as e:
        logger.error(f"❌ [NOMENCLATURE] Ошибка: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/employees/<employee_id>/dictionary', methods=['GET'])
def get_employee_dictionary_api(employee_id):
    return get_employee_dictionary(employee_id)


@app.route('/employees/<employee_id>/dictionary', methods=['GET'])
def get_employee_dictionary(employee_id):
    """Получить словарь для распознавания речи сотрудника"""
    logger.info(f"📖 [DICTIONARY] Запрос словаря сотрудника: {employee_id}")
    
    try:
        from models import EmployeeManager
        manager = EmployeeManager()
        manager.load_all()
        
        employee = manager.get_employee(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        dictionary = employee.get_voice_dictionary()
        speechkit_format = employee.get_yandex_speechkit_dictionary()
        
        logger.info(f"✅ [DICTIONARY] Терминов в словаре: {len(dictionary)}")
        return jsonify({
            'employee_id': employee_id,
            'dictionary': dictionary,
            'speechkit_format': speechkit_format,
            'total_terms': len(dictionary),
        })
    
    except Exception as e:
        logger.error(f"❌ [DICTIONARY] Ошибка: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Инициализация БД - создание таблиц
    print("\n🗄️  Инициализация базы данных...")
    try:
        from models_db import init_db, engine, Employee, Nomenclature, Client, VoiceDictionary, VoiceVariant, Order, OrderItem, UnitOfMeasure, UnitVariant, YandexCloudSettings
        from sqlalchemy import inspect, func, text

        # Создаем таблицы и добавляем недостающие колонки (ALTER TABLE ... ADD COLUMN IF NOT EXISTS)
        init_db()
        print("✅ Таблицы БД созданы/обновлены (схема проверена)")

        # === БЛОК САМОДИАГНОСТИКИ ===
        print("\n" + "=" * 70)
        print("🔍 САМОДИАГНОСТИКА БАЗЫ ДАННЫХ")
        print("=" * 70)

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📊 Всего таблиц в БД: {len(tables)}")
        print(f"   Таблицы: {', '.join(tables)}")

        # Ключевые колонки настроек ЯО — частая причина «не сохраняет»
        try:
            yc_cols = {c['name'] for c in inspector.get_columns('yandex_cloud_settings')}
            needed = {'api_key', 'folder_id', 'bucket_name',
                      'access_key_id', 'secret_access_key'}
            missing = needed - yc_cols
            if missing:
                print(f"❌ [SELF-CHECK] В таблице yandex_cloud_settings НЕТ колонок: {', '.join(missing)}")
            else:
                print("✅ [SELF-CHECK] Все колонки настроек Яндекс Облака на месте")
        except Exception as e:
            print(f"⚠️  [SELF-CHECK] Проверка колонок не выполнена: {e}")
        
        # Подсчет записей в каждой таблице
        from database import get_session, close_session
        session = get_session()
        
        print("\n📈 Количество записей:")
        try:
            emp_count = session.query(Employee).count()
            print(f"   • Сотрудники (employees): {emp_count}")
        except Exception as e:
            print(f"   • Сотрудники: ошибка ({e})")
        
        try:
            nom_count = session.query(Nomenclature).count()
            print(f"   • Номенклатура (nomenclature): {nom_count}")
        except Exception as e:
            print(f"   • Номенклатура: ошибка ({e})")
        
        try:
            cli_count = session.query(Client).count()
            print(f"   • Клиенты (clients): {cli_count}")
        except Exception as e:
            print(f"   • Клиенты: ошибка ({e})")
        
        try:
            dict_count = session.query(VoiceDictionary).count()
            var_count = session.query(VoiceVariant).count()
            print(f"   • Словарь (voice_dictionary): {dict_count} записей, {var_count} вариантов")
        except Exception as e:
            print(f"   • Словарь: ошибка ({e})")
        
        try:
            order_count = session.query(Order).count()
            item_count = session.query(OrderItem).count()
            print(f"   • Заказы (orders): {order_count} заказов, {item_count} позиций")
        except Exception as e:
            print(f"   • Заказы: ошибка ({e})")
        
        try:
            unit_count = session.query(UnitOfMeasure).count()
            unit_var_count = session.query(UnitVariant).count()
            print(f"   • Единицы измерения: {unit_count} единиц, {unit_var_count} вариантов")
        except Exception as e:
            print(f"   • Единицы измерения: ошибка ({e})")
        
        try:
            settings_count = session.query(YandexCloudSettings).count()
            print(f"   • Настройки Яндекс Облака: {settings_count}")
        except Exception as e:
            print(f"   • Настройки Яндекс Облака: ошибка ({e})")
        
        close_session()
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"⚠️  Ошибка инициализации БД: {e}")
    
    print("\n" + "=" * 70)
    print("🎤 Audio Analyzer Backend")
    print("=" * 70)
    print("🌐 Сервер запущен: http://localhost:5000")
    print("📡 Доступные эндпоинты:")
    print("   GET  /health                              — проверка работоспособности")
    print("   POST /recognize                           — распознавание речи (+ опц. разбор заказа через YandexGPT: process_llm=true)")
    print("   POST /process-order                       — разбор текста расшифровки в список заказа (YandexGPT)")
    print("   POST /analyze                             — анализ аудио")
    print("   POST /analyze-xlsx                        — анализ XLSX файлов")
    print("   GET  /employees                           — список сотрудников")
    print("   GET  /employees/<id>                      — информация о сотруднике")
    print("   GET  /employees/<id>/nomenclature         — номенклатура сотрудника")
    print("   GET  /employees/<id>/dictionary           — словарь для распознавания")
    print("=" * 70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
