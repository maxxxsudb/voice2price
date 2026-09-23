import { useState } from 'react';
import type { AudioFile } from '../types';

interface Props {
  files: AudioFile[];
}

const BACKEND_SCRIPT = `#!/usr/bin/env python3
"""
Бэкенд для аудио-анализатора.
Flask-сервер: принимает MP3, загружает в Object Storage (Yandex Cloud),
отправляет ссылку в SpeechKit longRunningRecognize, ждёт операцию и
возвращает распознанный текст.

Запуск:
    pip install flask flask-cors requests boto3 pydub
    python backend/server.py

Сервер запустится на http://localhost:5000
"""

import os
import time
import tempfile
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import boto3

# ==================== НАСТРОЙКИ ====================

app = Flask(__name__)
CORS(app)  # Разрешаем запросы из браузера

YC_STT_LONGRUNNING_URL = "https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize"
OPERATION_API_URL = "https://operation.api.cloud.yandex.net/operations"
S3_ENDPOINT_URL = "https://storage.yandexcloud.net"


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


# ==================== РАСПОЗНАВАНИЕ (рабочая схема) ====================


def upload_to_object_storage(local_path: str, object_key: str, access_key_id: str,
                             secret_access_key: str, bucket: str) -> str:
    """Шаг 1. Загружаем файл в Object Storage, возвращаем uri."""
    s3 = boto3.session.Session().client(
        service_name='s3',
        endpoint_url=S3_ENDPOINT_URL,
        region_name='ru-central1',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
    )
    s3.upload_file(Filename=local_path, Bucket=bucket, Key=object_key)
    return f"{S3_ENDPOINT_URL}/{bucket}/{object_key}"


def recognize_via_storage_uri(audio_uri: str, api_key: str, folder_id: str,
                              encoding: str = 'MP3', sample_rate: int = 48000,
                              language: str = 'ru-RU', model: str = 'general') -> str:
    """Шаги 2-4. longRunningRecognize по uri + опрос операции + склейка текста."""
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
                'audioChannelCount': 1,
                'rawResults': False,
            }
        },
        'audio': {'uri': audio_uri},
    }
    resp = requests.post(YC_STT_LONGRUNNING_URL, headers=headers, json=body, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f'SpeechKit longRunningRecognize ошибка {resp.status_code}: {resp.text[:500]}')
    op_id = resp.json()['id']

    op_url = f"{OPERATION_API_URL}/{op_id}"
    while True:
        op = requests.get(op_url, headers=headers, timeout=30).json()
        if op.get('done'):
            break
        time.sleep(5)

    if 'error' in op:
        raise RuntimeError(f"SpeechKit вернул ошибку операции: {op['error']}")

    response = op.get('response', {})
    return ' '.join(
        chunk.get('alternatives', [{}])[0].get('text', '')
        for chunk in response.get('chunks', [])
    ).strip()


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
        - file: аудиофайл (MP3)
        - api_key: API-ключ сервисного аккаунта SpeechKit
        - folder_id: Folder ID
        - access_key_id / secret_access_key: S3-ключи сервисного аккаунта
        - bucket: имя бакета Object Storage
        - language: (опционально, по умолчанию ru-RU)
        - model: (опционально, по умолчанию general)
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    api_key = request.form.get('api_key', '')
    folder_id = request.form.get('folder_id', '')
    access_key_id = request.form.get('access_key_id', '')
    secret_access_key = request.form.get('secret_access_key', '')
    bucket = request.form.get('bucket', '')
    language = request.form.get('language', 'ru-RU')
    model = request.form.get('model', 'general')

    if not api_key:
        return jsonify({'error': 'api_key is required'}), 400
    if not (access_key_id and secret_access_key and bucket):
        return jsonify({'error': 'access_key_id, secret_access_key и bucket обязательны (Object Storage)'}), 400

    # Сохраняем файл во временный
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        # Анализ аудио (частота дискретизации берётся из файла)
        audio_info = analyze_audio(tmp_path)
        sample_rate = int(audio_info.get('sample_rate') or 48000)

        # Шаг 1: загрузка в Object Storage
        object_key = f"audio-uploads/{datetime.now().strftime('%Y%m%d-%H%M%S')}-{Path(file.filename).name}"
        audio_uri = upload_to_object_storage(tmp_path, object_key, access_key_id, secret_access_key, bucket)

        # Шаги 2-4: longRunningRecognize -> опрос операции -> текст
        text = recognize_via_storage_uri(
            audio_uri, api_key, folder_id,
            encoding='MP3', sample_rate=sample_rate, language=language, model=model)

        return jsonify({
            'text': text,
            'audio_info': audio_info,
            'object_uri': audio_uri,
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

export default function PythonScriptGenerator({ files }: Props) {
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
