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
    return jsonify({
        'status': 'ok',
        'service': 'audio-analyzer-backend',
        'version': '1.0.0',
    })


@app.route('/recognize', methods=['POST'])
def recognize():
    """Распознавание речи"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    api_key = request.form.get('api_key', '')
    folder_id = request.form.get('folder_id', '')
    language = request.form.get('language', 'ru-RU')
    model = request.form.get('model', 'general')

    if not api_key:
        return jsonify({'error': 'api_key is required'}), 400

    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        audio_info = analyze_audio(tmp_path)
        pcm_data = convert_to_pcm(tmp_path)

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

        result = response.json()
        text = result.get('result', '')

        return jsonify({
            'text': text,
            'confidence': result.get('confidence', 0),
            'audio_info': audio_info,
            'raw_response': result,
            'pcm_size': len(pcm_data),
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


if __name__ == '__main__':
    print("=" * 50)
    print("🎤 Audio Analyzer Backend")
    print("=" * 50)
    print("🌐 Сервер запущен: http://localhost:5000")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
