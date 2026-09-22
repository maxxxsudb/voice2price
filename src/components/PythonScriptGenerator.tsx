import { useState } from 'react';
import type { ApiConfig, AudioFile } from '../types';

interface Props {
  config: ApiConfig;
  files: AudioFile[];
}

const BACKEND_SCRIPT = `#!/usr/bin/env python3
"""
Бэкенд для аудио-анализатора.
Flask-сервер, который принимает MP3 файлы, конвертирует в PCM,
отправляет в Яндекс SpeechKit и возвращает распознанный текст.

Запуск:
    pip install flask pydub requests
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
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    api_key = request.form.get('api_key', '')
    folder_id = request.form.get('folder_id', '')
    language = request.form.get('language', 'ru-RU')
    model = request.form.get('model', 'general')

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
`;

export default function PythonScriptGenerator({ config, files }: Props) {
  const [copied, setCopied] = useState(false);
  const [activeSection, setActiveSection] = useState<'backend' | 'standalone'>('backend');

  const handleCopy = () => {
    navigator.clipboard.writeText(BACKEND_SCRIPT);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([BACKEND_SCRIPT], { type: 'text/x-python' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'server.py';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Explanation */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <h2 className="text-white font-bold text-lg mb-3 flex items-center gap-2">
          <i className="fas fa-server text-green-400"></i>
          Бэкенд — Flask сервер
        </h2>
        <p className="text-gray-300 text-sm mb-4">
          Фронтенд (эта страница) не может напрямую обращаться к SpeechKit API из-за CORS-политик Яндекса.
          Нужен бэкенд — маленький Flask-сервер, который:
        </p>
        <ul className="text-gray-400 text-sm space-y-1 list-disc list-inside">
          <li>Принимает MP3 файлы от фронтенда</li>
          <li>Конвертирует их в PCM 16kHz mono</li>
          <li>Отправляет в SpeechKit API</li>
          <li>Возвращает распознанный текст</li>
        </ul>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveSection('backend')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeSection === 'backend' ? 'bg-green-500/20 text-green-300' : 'bg-white/5 text-gray-400 hover:bg-white/10'
          }`}
        >
          <i className="fas fa-server mr-2"></i>Бэкенд (server.py)
        </button>
        <button
          onClick={() => setActiveSection('standalone')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeSection === 'standalone' ? 'bg-purple-500/20 text-purple-300' : 'bg-white/5 text-gray-400 hover:bg-white/10'
          }`}
        >
          <i className="fas fa-terminal mr-2"></i>Автономный скрипт
        </button>
      </div>

      {activeSection === 'backend' && (
        <>
          {/* Install instructions */}
          <div className="bg-green-500/10 border border-green-500/20 rounded-2xl p-6">
            <h3 className="text-green-300 font-semibold mb-3">🚀 Как запустить</h3>
            <div className="space-y-2 text-sm">
              <div className="bg-black/30 rounded-lg p-3 font-mono text-green-300 text-xs">
                <p># 1. Установить зависимости</p>
                <p>pip install flask flask-cors requests pydub</p>
                <p className="mt-2"># 2. Установить ffmpeg (если pydub не найдёт)</p>
                <p># macOS: brew install ffmpeg</p>
                <p># Ubuntu: sudo apt install ffmpeg</p>
                <p># Windows: скачать с ffmpeg.org, добавить в PATH</p>
                <p className="mt-2"># 3. Сохранить файл и запустить</p>
                <p>python server.py</p>
                <p className="mt-2"># Сервер запустится на http://localhost:5000</p>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={handleDownload}
              className="flex-1 py-3 rounded-xl bg-gradient-to-r from-green-500/20 to-emerald-500/20 border border-green-500/30 text-green-300 font-medium hover:from-green-500/30 hover:to-emerald-500/30 transition-all flex items-center justify-center gap-2"
            >
              <i className="fas fa-download"></i>
              Скачать server.py
            </button>
            <button
              onClick={handleCopy}
              className={`px-5 py-3 rounded-xl border font-medium transition-all flex items-center gap-2 ${
                copied
                  ? 'bg-green-500/20 border-green-500/30 text-green-300'
                  : 'bg-white/5 border-white/10 text-gray-300 hover:bg-white/10'
              }`}
            >
              <i className={`fas ${copied ? 'fa-check' : 'fa-copy'}`}></i>
              {copied ? 'Скопировано' : 'Копировать'}
            </button>
          </div>

          {/* Script */}
          <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-white/5">
              <span className="text-gray-300 text-sm font-medium flex items-center gap-2">
                <i className="fab fa-python text-yellow-400"></i>
                backend/server.py
              </span>
              <span className="text-gray-500 text-xs">{BACKEND_SCRIPT.split('\n').length} строк</span>
            </div>
            <pre className="p-4 text-xs text-gray-300 overflow-x-auto max-h-[600px] overflow-y-auto font-mono leading-relaxed">
              {BACKEND_SCRIPT}
            </pre>
          </div>
        </>
      )}

      {activeSection === 'standalone' && (
        <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
          <h3 className="text-white font-semibold mb-3">Автономный скрипт (без фронтенда)</h3>
          <p className="text-gray-400 text-sm mb-4">
            Если хотите обрабатывать файлы без UI — используйте скрипт из вкладки "Python скрипт"
            в предыдущей версии, либо запустите бэкенд и используйте curl:
          </p>
          <div className="bg-black/30 rounded-lg p-3 font-mono text-xs text-green-300 space-y-2">
            <p># Распознать файл:</p>
            <p>curl -X POST http://localhost:5000/recognize \</p>
            <p>  -F "file=@audio.mp3" \</p>
            <p>  -F "api_key=YOUR_KEY" \</p>
            <p>  -F "language=ru-RU"</p>
            <p className="mt-3"># Анализ файла:</p>
            <p>curl -X POST http://localhost:5000/analyze \</p>
            <p>  -F "file=@audio.mp3"</p>
          </div>
        </div>
      )}

      {/* Info about files */}
      {files.length > 0 && (
        <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
          <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
            <i className="fas fa-info-circle text-blue-400"></i>
            Информация о загруженных файлах
          </h3>
          <div className="space-y-2">
            {files.map((file) => (
              <div key={file.id} className="flex items-center gap-3 bg-white/5 rounded-lg px-4 py-2">
                <i className="fas fa-music text-purple-400"></i>
                <span className="text-white text-sm flex-1">{file.name}</span>
                <span className="text-gray-400 text-xs">{(file.size / 1024 / 1024).toFixed(2)} МБ</span>
                {file.duration && (
                  <span className="text-gray-400 text-xs">
                    {Math.floor(file.duration / 60)}:{String(Math.floor(file.duration % 60)).padStart(2, '0')}
                  </span>
                )}
              </div>
            ))}
          </div>
          <p className="text-gray-500 text-xs mt-3">
            * Файлы загружены только в вашем браузере. Для распознавания нужен запущенный бэкенд.
          </p>
        </div>
      )}
    </div>
  );
}
