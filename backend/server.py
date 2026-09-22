#!/usr/bin/env python3
"""
Backend сервер для аудио-анализатора.
Принимает MP3 файлы, конвертирует в PCM, отправляет в Яндекс SpeechKit.
"""

import os
import io
import tempfile
import subprocess
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

SPEECHKIT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"


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
    """Распознавание речи"""
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

    print(f"✅ [RECOGNIZE] Получен файл: {file.filename}")
    print(f"   Язык: {language}, Модель: {model}")
    
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

        print("="*70)
        print("✅ [RECOGNIZE] Возвращаем результат")
        print("="*70 + "\n")
        
        return jsonify({
            'text': text,
            'confidence': result.get('confidence', 0),
            'audio_info': audio_info,
            'raw_response': result,
            'pcm_size': len(pcm_data),
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
    print("\n" + "="*70)
    print("📊 [XLSX ANALYZE] Начало анализа файла")
    print("="*70)
    
    if 'file' not in request.files:
        print("❌ [XLSX ANALYZE] Файл не предоставлен в запросе")
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    print(f"✅ [XLSX ANALYZE] Получен файл: {file.filename}")
    print(f"   Размер: {file.content_length} байт" if file.content_length else "   Размер: неизвестен")
    
    # Проверяем расширение
    if not file.filename.lower().endswith('.xlsx'):
        print(f"❌ [XLSX ANALYZE] Неправильное расширение: {file.filename}")
        return jsonify({'error': 'Файл должен быть .xlsx'}), 400

    tmp_path = None
    try:
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        print(f"💾 [XLSX ANALYZE] Файл сохранён: {tmp_path}")
        
        # Импортируем анализатор
        print("📦 [XLSX ANALYZE] Импортируем модуль analyze_xlsx...")
        try:
            from analyze_xlsx import analyze_xlsx as analyze_file
            print("✅ [XLSX ANALYZE] Модуль успешно импортирован")
        except ImportError as e:
            print(f"❌ [XLSX ANALYZE] Ошибка импорта модуля: {e}")
            return jsonify({'error': f'Ошибка импорта модуля: {str(e)}'}), 500
        
        # Анализируем файл
        print("🔍 [XLSX ANALYZE] Начинаем анализ файла...")
        result = analyze_file(tmp_path)
        
        print(f"✅ [XLSX ANALYZE] Анализ завершён успешно")
        print(f"   Найдено листов: {len(result.get('sheets', []))}")
        
        for idx, sheet in enumerate(result.get('sheets', []), 1):
            print(f"   Лист {idx}: {sheet.get('name')} ({sheet.get('max_row')} строк × {sheet.get('max_column')} колонок)")
        
        print("="*70)
        print("✅ [XLSX ANALYZE] Возвращаем результат клиенту")
        print("="*70 + "\n")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"\n❌ [XLSX ANALYZE] КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        print("="*70 + "\n")
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                print(f"🗑️  [XLSX ANALYZE] Временный файл удалён: {tmp_path}")
            except Exception as e:
                print(f"⚠️  [XLSX ANALYZE] Не удалось удалить временный файл: {e}")


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🎤 Audio Analyzer Backend")
    print("=" * 70)
    print("🌐 Сервер запущен: http://localhost:5000")
    print("📡 Доступные эндпоинты:")
    print("   GET  /health         — проверка работоспособности")
    print("   POST /recognize      — распознавание речи")
    print("   POST /analyze        — анализ аудио")
    print("   POST /analyze-xlsx   — анализ XLSX файлов")
    print("=" * 70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
