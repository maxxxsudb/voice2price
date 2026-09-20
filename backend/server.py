#!/usr/bin/env python3
"""
Бэкенд для аудио-анализатора.
Flask-сервер, который принимает MP3 файлы, конвертирует в PCM,
отправляет в Яндекс SpeechKit и возвращает распознанный текст.

Запуск:
    pip install flask flask-cors requests pydub
    python backend/server.py

Сервер запустится на http://localhost:5000
"""

import os
import io
import json
import tempfile
import subprocess
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# ==================== НАСТРОЙКИ ====================

app = Flask(__name__)
CORS(app)  # Разрешаем запросы из браузера

SPEECHKIT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"

# ==================== КОНВЕРТАЦИЯ ====================


def convert_to_pcm(input_path: str) -> bytes:
    """
    Конвертирует аудиофайл в PCM 16kHz mono 16bit.
    Пробует pydub, если не установлен — использует ffmpeg напрямую.
    """
    # Пробуем pydub
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(input_path)
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        return audio.raw_data
    except ImportError:
        pass

    # Fallback: ffmpeg напрямую
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
    """Анализ аудиофайла: длительность, громкость, и т.д."""
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


# ==================== РЕКОГНИЦИЯ ====================


def recognize_speech(pcm_data: bytes, api_key: str, language: str = 'ru-RU', model: str = 'general', folder_id: str = '') -> dict:
    """Отправляет PCM в SpeechKit и возвращает результат"""
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
        raise Exception(f"SpeechKit API error {response.status_code}: {response.text}")

    return response.json()


# ==================== ПОИСК НОМЕНКЛАТУРЫ ====================


def search_nomenclature(text: str, terms: list) -> list:
    """Поиск терминов номенклатуры в тексте"""
    if not text or not terms:
        return []
    
    matches = []
    text_lower = text.lower()
    
    for term in terms:
        term_lower = term.lower()
        start = 0
        while True:
            pos = text_lower.find(term_lower, start)
            if pos == -1:
                break
            ctx_start = max(0, pos - 50)
            ctx_end = min(len(text), pos + len(term) + 50)
            matches.append({
                'term': term,
                'position': pos,
                'context': text[ctx_start:ctx_end].strip(),
            })
            start = pos + 1
    
    return matches


# ==================== ENDPOINTS ====================


@app.route('/health', methods=['GET'])
def health():
    """Проверка работоспособности"""
    return jsonify({
        'status': 'ok',
        'service': 'audio-analyzer-backend',
        'version': '1.0.0',
    })


@app.route('/recognize', methods=['POST'])
def recognize():
    """
    Принимает аудиофайл, распознаёт речь.
    
    Параметры (multipart/form-data):
        - file: аудиофайл (MP3, WAV, OGG, ...)
        - api_key: API-ключ Яндекс SpeechKit
        - folder_id: (опционально) Folder ID
        - language: (опционально, по умолчанию ru-RU)
        - model: (опционально, по умолчанию general)
        - nomenclature: (опционально) JSON-массив терминов для поиска
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    api_key = request.form.get('api_key', '')
    folder_id = request.form.get('folder_id', '')
    language = request.form.get('language', 'ru-RU')
    model = request.form.get('model', 'general')
    nomenclature_raw = request.form.get('nomenclature', '[]')
    
    try:
        nomenclature = json.loads(nomenclature_raw)
    except:
        nomenclature = []

    if not api_key:
        return jsonify({'error': 'api_key is required'}), 400

    # Сохраняем файл во временный
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        # Анализ аудио
        audio_info = analyze_audio(tmp_path)

        # Конвертация в PCM
        pcm_data = convert_to_pcm(tmp_path)

        # Распознавание
        result = recognize_speech(pcm_data, api_key, language, model, folder_id)
        text = result.get('result', '')

        # Поиск номенклатуры
        nomenclature_matches = search_nomenclature(text, nomenclature)

        return jsonify({
            'text': text,
            'confidence': result.get('confidence', 0),
            'audio_info': audio_info,
            'raw_response': result,
            'pcm_size': len(pcm_data),
            'nomenclature_matches': nomenclature_matches,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.route('/analyze', methods=['POST'])
def analyze():
    """Только анализ файла без распознавания"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        info = analyze_audio(tmp_path)
        info['file_name'] = file.filename
        info['file_size'] = os.path.getsize(tmp_path)
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ==================== ЗАПУСК ====================

if __name__ == '__main__':
    print("=" * 50)
    print("🎤 Audio Analyzer Backend")
    print("=" * 50)
    print("🌐 Сервер запущен: http://localhost:5000")
    print("📡 Endpoints:")
    print("   GET  /health    — проверка работоспособности")
    print("   POST /recognize — распознавание речи")
    print("   POST /analyze   — анализ аудио")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
