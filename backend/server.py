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

SPEECHKIT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
SPEECHKIT_ASYNC_URL = "https://stt.api.cloud.yandex.net/stt/v3/recognizeFileAsync"
OPERATION_API_URL = "https://operation.api.cloud.yandex.net/operations"

# Регистрируем blueprint для работы с сотрудниками
from api_employees import employees_bp
app.register_blueprint(employees_bp)

# Регистрируем blueprint для работы с Яндекс Облаком (настройки, IAM токен, Object Storage)
from api_yandex_cloud import yandex_cloud_bp
app.register_blueprint(yandex_cloud_bp)


def recognize_speech_async(audio_data: bytes, api_key: str, language: str = 'ru-RU', 
                           model: str = 'deferred-general', folder_id: str = '',
                           audio_format: str = 'MP3') -> dict:
    """
    Асинхронное распознавание речи для больших файлов (API v3).
    
    Args:
        audio_data: Байты аудиофайла
        api_key: API ключ SpeechKit
        language: Язык (ru-RU, en-US, etc.)
        model: Модель распознавания (deferred-general для больших файлов)
        folder_id: Folder ID
        audio_format: Формат аудио (MP3, WAV, OGG_OPUS, LINEAR16_PCM)
    
    Returns:
        Результат распознавания
    """
    import time
    import base64
    
    print(f"🎤 [ASYNC] Запуск асинхронного распознавания...")
    print(f"   Размер файла: {len(audio_data) / 1024 / 1024:.2f} МБ")
    print(f"   Модель: {model}")
    print(f"   Формат: {audio_format}")
    
    # Формируем запрос для API v3
    headers = {
        'Authorization': f'Api-Key {api_key}',
        'Content-Type': 'application/json'
    }
    
    if folder_id:
        headers['x-folder-id'] = folder_id
    
    # Определяем формат аудио
    if audio_format == 'MP3':
        audio_config = {
            "containerAudio": {
                "containerAudioType": "MP3"
            }
        }
    elif audio_format == 'WAV':
        audio_config = {
            "containerAudio": {
                "containerAudioType": "WAV"
            }
        }
    elif audio_format == 'OGG_OPUS':
        audio_config = {
            "containerAudio": {
                "containerAudioType": "OGG_OPUS"
            }
        }
    else:  # LINEAR16_PCM
        audio_config = {
            "rawAudio": {
                "audioEncoding": "LINEAR16_PCM",
                "sampleRateHertz": "16000",
                "audioChannelCount": "1"
            }
        }
    
    # Кодируем аудио в base64
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    request_body = {
        "content": audio_base64,
        "recognitionModel": {
            "model": model,
            "audioFormat": audio_config,
            "languageRestriction": {
                "restrictionType": "WHITELIST",
                "languageCode": [language]
            }
        }
    }
    
    # Отправляем запрос на асинхронное распознавание
    print(f"🚀 [ASYNC] Отправка запроса на {SPEECHKIT_ASYNC_URL}")
    response = requests.post(
        SPEECHKIT_ASYNC_URL,
        headers=headers,
        json=request_body,
        timeout=120
    )
    
    if response.status_code != 200:
        print(f"❌ [ASYNC] Ошибка API: {response.status_code}")
        print(f"   Ответ: {response.text}")
        raise Exception(f"SpeechKit Async API error {response.status_code}: {response.text}")
    
    operation = response.json()
    operation_id = operation.get('id')
    
    if not operation_id:
        raise Exception(f"Не получен operation_id из ответа: {operation}")
    
    print(f"✅ [ASYNC] Операция создана: {operation_id}")
    
    # Polling для получения результата
    print(f"🔄 [ASYNC] Ожидание результата...")
    print(f"   Интервал проверки: каждые 5 секунд")
    print(f"   Максимум попыток: 120 (10 минут)")
    max_attempts = 120  # Максимум 10 минут (120 * 5 секунд)
    attempt = 0
    
    while attempt < max_attempts:
        time.sleep(5)  # Ждём 5 секунд между запросами
        attempt += 1
        
        # Проверяем статус операции
        check_headers = {
            'Authorization': f'Api-Key {api_key}'
        }
        
        check_response = requests.get(
            f"{OPERATION_API_URL}/{operation_id}",
            headers=check_headers,
            timeout=30
        )
        
        if check_response.status_code != 200:
            print(f"⚠️  [ASYNC] Ошибка проверки статуса: {check_response.status_code}")
            print(f"   Ответ: {check_response.text[:200]}")
            continue
        
        operation = check_response.json()
        done = operation.get('done', False)
        
        print(f"   Попытка {attempt}/{max_attempts}: done={done}")
        
        if done:
            print(f"✅ [ASYNC] Операция завершена!")
            print(f"   Ключи в ответе: {list(operation.keys())}")
            
            # Проверяем есть ли ошибка
            if 'error' in operation:
                error = operation['error']
                print(f"❌ [ASYNC] Ошибка распознавания: {error}")
                raise Exception(f"Ошибка распознавания: {error.get('message', 'Неизвестная ошибка')}")
            
            # Получаем результат
            if 'response' in operation:
                result = operation['response']
                print(f"✅ [ASYNC] Результат получен!")
                print(f"   Ключи в response: {list(result.keys())}")
                
                # Извлекаем текст из chunks
                chunks = result.get('chunks', [])
                print(f"   Найдено chunks: {len(chunks)}")
                
                if len(chunks) == 0:
                    print(f"⚠️  [ASYNC] Chunks пустой - возможно в аудио нет речи")
                    print(f"   Полный response: {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}")
                    return {
                        'result': '',
                        'chunks': [],
                        'operation_id': operation_id
                    }
                
                full_text = ''
                for idx, chunk in enumerate(chunks):
                    alternatives = chunk.get('alternatives', [])
                    if alternatives:
                        text = alternatives[0].get('text', '')
                        full_text += text + ' '
                        if idx < 3:  # Показываем первые 3 chunks
                            print(f"   Chunk {idx}: {text[:50]}...")
                    else:
                        print(f"   ⚠️  Chunk {idx}: нет alternatives")
                
                print(f"✅ [ASYNC] Распознавание завершено!")
                print(f"   Итоговый текст: {len(full_text)} символов")
                
                return {
                    'result': full_text.strip(),
                    'chunks': chunks,
                    'operation_id': operation_id
                }
            else:
                # done=True но response отсутствует
                # Возможно результат ещё обрабатывается или произошла ошибка
                print(f"⚠️  [ASYNC] done=True но response отсутствует")
                print(f"   Проверяем метаданные...")
                
                # Логируем полный ответ для отладки
                operation_json = json.dumps(operation, indent=2, ensure_ascii=False)
                print(f"   Полный ответ операции:")
                print(f"   {operation_json[:2000]}")
                
                # Проверяем метаданные
                metadata = operation.get('metadata', {})
                if metadata:
                    print(f"   Метаданные: {json.dumps(metadata, indent=2, ensure_ascii=False)[:500]}")
                
                # Если это первая попытка после done=True - подождём ещё
                if attempt < max_attempts - 5:
                    print(f"   Ждём ещё 10 секунд...")
                    time.sleep(10)
                    continue
                else:
                    raise Exception("Результат не найден в ответе операции. Проверьте логи бэкенда.")
    
    raise Exception(f"Превышено время ожидания ({max_attempts * 5} секунд)")


def convert_to_pcm(input_path: str) -> bytes:
    """Конвертирует аудио в PCM 16kHz mono 16bit"""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(input_path)
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        return audio.raw_data
    except ImportError:
        # Fallback на ffmpeg
        with tempfile.NamedTemporaryFile(suffix='.raw', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            subprocess.run(
                [
                    'ffmpeg', '-y', '-i', input_path,
                    '-ar', '16000', '-ac', '1',
                    '-f', 's16le', '-acodec', 'pcm_s16le',
                    tmp_path
                ],
                check=True,
                capture_output=True,
            )
            with open(tmp_path, 'rb') as f:
                return f.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


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


@app.route('/health', methods=['GET'])
def health():
    """Проверка работоспособности"""
    print("✅ [HEALTH] Запрос проверки работоспособности")
    return jsonify({
        'status': 'ok',
        'service': 'audio-analyzer-backend',
        'version': '1.0.0',
    })


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
    
    if not api_key:
        print("❌ [RECOGNIZE] API ключ не предоставлен")
        return jsonify({'error': 'api_key is required'}), 400

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
        
        # Решаем какой API использовать
        # Синхронный API имеет лимит 1 МБ для PCM
        # Для больших файлов используем асинхронный API v3
        use_async = file_size > 1_000_000  # > 1 МБ
        
        if use_async:
            print(f"🚀 [RECOGNIZE] Файл большой - используем АСИНХРОННЫЙ API v3")
            
            # Определяем формат файла
            file_ext = Path(file.filename).suffix.lower()
            if file_ext == '.mp3':
                audio_format = 'MP3'
            elif file_ext == '.wav':
                audio_format = 'WAV'
            elif file_ext in ['.ogg', '.opus']:
                audio_format = 'OGG_OPUS'
            else:
                # Для неизвестных форматов конвертируем в PCM
                print(f"🔄 [RECOGNIZE] Неизвестный формат {file_ext}, конвертируем в PCM...")
                pcm_data = convert_to_pcm(tmp_path)
                audio_format = 'LINEAR16_PCM'
                audio_data = pcm_data
            
            if audio_format != 'LINEAR16_PCM':
                # Читаем файл напрямую
                with open(tmp_path, 'rb') as f:
                    audio_data = f.read()
            
            # Используем модель deferred-general для больших файлов
            async_model = 'deferred-general' if model == 'general' else f'deferred-{model}'
            
            result = recognize_speech_async(
                audio_data=audio_data,
                api_key=api_key,
                language=language,
                model=async_model,
                folder_id=folder_id,
                audio_format=audio_format
            )
            text = result.get('result', '')
            pcm_data = audio_data  # Для совместимости
            
        else:
            print(f"🚀 [RECOGNIZE] Файл маленький - используем СИНХРОННЫЙ API")
            print("🔄 [RECOGNIZE] Конвертируем в PCM...")
            pcm_data = convert_to_pcm(tmp_path)
            print(f"✅ [RECOGNIZE] PCM размер: {len(pcm_data)} байт")

            print("🚀 [RECOGNIZE] Отправляем в SpeechKit...")
            params = {
                'topic': model,
                'lang': language,
                'format': 'lpcm',
                'sampleRateHertz': '16000',
            }
            if folder_id:
                params['folderId'] = folder_id

            headers = {'Authorization': f'Api-Key {api_key}'}
            response = requests.post(SPEECHKIT_URL, params=params, headers=headers, data=pcm_data, timeout=60)

            if response.status_code != 200:
                print(f"❌ [RECOGNIZE] Ошибка SpeechKit API: {response.status_code}")
                raise Exception(f"SpeechKit API error {response.status_code}: {response.text}")

            result = response.json()
            text = result.get('result', '')
        
        print(f"✅ [RECOGNIZE] Распознано: {len(text)} символов")
        print(f"   Текст: {text[:100]}..." if len(text) > 100 else f"   Текст: {text}")

        # Если указан сотрудник - используем словарь и парсим заказ
        parsed_order = None
        if employee_id and text:
            print(f"\n🔍 [RECOGNIZE] Парсим заказ для сотрудника {employee_id}...")
            from models import EmployeeManager
            manager = EmployeeManager()
            manager.load_all()
            employee = manager.get_employee(employee_id)
            
            if employee:
                # Парсим текст заказа
                parsed_order = employee.parse_order_text(text)
                
                print(f"✅ [RECOGNIZE] Заказ распарсен:")
                if parsed_order['clients']:
                    print(f"   Клиент: {parsed_order['clients'][0]['entry']['original']}")
                if parsed_order['nomenclatures']:
                    print(f"   Номенклатура: {len(parsed_order['nomenclatures'])} позиций")
                    for nom in parsed_order['nomenclatures']:
                        print(f"     • {nom['entry']['original']}")
                if parsed_order['quantities']:
                    print(f"   Количества: {parsed_order['quantities']}")
            else:
                print(f"⚠️  [RECOGNIZE] Сотрудник {employee_id} не найден")

        print("="*70)
        print("✅ [RECOGNIZE] Возвращаем результат")
        print("="*70 + "\n")
        
        return jsonify({
            'text': text,
            'confidence': result.get('confidence', 0),
            'audio_info': audio_info,
            'raw_response': result,
            'pcm_size': len(pcm_data),
            'parsed_order': parsed_order,
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
    print("\n" + "=" * 70)
    print("🎤 Audio Analyzer Backend")
    print("=" * 70)
    print("🌐 Сервер запущен: http://localhost:5000")
    print("📡 Доступные эндпоинты:")
    print("   GET  /health                              — проверка работоспособности")
    print("   POST /recognize                           — распознавание речи")
    print("   POST /analyze                             — анализ аудио")
    print("   POST /analyze-xlsx                        — анализ XLSX файлов")
    print("   GET  /employees                           — список сотрудников")
    print("   GET  /employees/<id>                      — информация о сотруднике")
    print("   GET  /employees/<id>/nomenclature         — номенклатура сотрудника")
    print("   GET  /employees/<id>/dictionary           — словарь для распознавания")
    print("=" * 70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
