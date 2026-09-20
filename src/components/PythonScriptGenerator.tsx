import { useState } from 'react';
import type { ApiConfig, AudioFile } from '../types';

interface Props {
  config: ApiConfig;
  files: AudioFile[];
}

export default function PythonScriptGenerator({ config, files }: Props) {
  const [copied, setCopied] = useState(false);
  const [nomenclatureInput, setNomenclatureInput] = useState('');
  const [nomenclatureTerms, setNomenclatureTerms] = useState<string[]>([]);

  const addTerm = () => {
    if (nomenclatureInput.trim() && !nomenclatureTerms.includes(nomenclatureInput.trim())) {
      setNomenclatureTerms([...nomenclatureTerms, nomenclatureInput.trim()]);
      setNomenclatureInput('');
    }
  };

  const removeTerm = (term: string) => {
    setNomenclatureTerms(nomenclatureTerms.filter(t => t !== term));
  };

  const fileNames = files.map(f => f.name);
  const termsStr = nomenclatureTerms.map(t => `    "${t}"`).join(',\n');

  const script = `#!/usr/bin/env python3
"""
Аудио анализатор с Яндекс SpeechKit
Распознавание речи из MP3 файлов и поиск номенклатуры
"""

import os
import json
import requests
import base64
from pathlib import Path
from typing import List, Dict, Optional

# ==================== НАСТРОЙКИ ====================

API_KEY = "${config.apiKey || 'YOUR_API_KEY_HERE'}"
FOLDER_ID = "${config.folderId || 'YOUR_FOLDER_ID'}"
LANGUAGE = "${config.language}"
MODEL = "${config.model}"

# Директория с MP3 файлами
AUDIO_DIR = "./audio_files"

# Номенклатура для поиска
NOMENCLATURE = [
${termsStr || '    # Добавьте термины для поиска\n    # "термин1",\n    # "термин2",'}
]

# ==================== ФУНКЦИИ ====================

def get_audio_files(directory: str) -> List[Path]:
    """Получить список аудиофайлов из директории"""
    audio_dir = Path(directory)
    extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}
    files = [f for f in audio_dir.iterdir() if f.suffix.lower() in extensions]
    return sorted(files)


def convert_to_pcm(audio_path: str) -> bytes:
    """
    Конвертировать аудиофайл в PCM 16kHz mono 16bit
    Использует pydub (нужен ffmpeg)
    """
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(audio_path)
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        return audio.raw_data
    except ImportError:
        print("⚠️  Установите pydub: pip install pydub")
        print("   Также нужен ffmpeg: https://ffmpeg.org/")
        raise


def convert_with_ffmpeg_subprocess(audio_path: str) -> bytes:
    """Альтернативная конвертация через ffmpeg subprocess"""
    import subprocess
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix='.raw', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        subprocess.run([
            'ffmpeg', '-i', audio_path,
            '-ar', '16000', '-ac', '1',
            '-f', 's16le', '-acodec', 'pcm_s16le',
            tmp_path
        ], check=True, capture_output=True)
        
        with open(tmp_path, 'rb') as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def recognize_speech(audio_data: bytes, api_key: str = None) -> Dict:
    """
    Отправить аудио на распознавание в Яндекс SpeechKit
    """
    key = api_key or API_KEY
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    
    params = {
        'topic': MODEL,
        'lang': LANGUAGE,
        'format': 'lpcm',
        'sampleRateHertz': '16000',
    }
    
    if FOLDER_ID and FOLDER_ID != 'YOUR_FOLDER_ID':
        params['folderId'] = FOLDER_ID
    
    headers = {
        'Authorization': f'Api-Key {key}',
    }
    
    response = requests.post(url, params=params, headers=headers, data=audio_data)
    
    if response.status_code != 200:
        raise Exception(f"Ошибка API: {response.status_code} - {response.text}")
    
    return response.json()


def search_nomenclature(text: str, terms: List[str]) -> List[Dict]:
    """Поиск номенклатуры в распознанном тексте"""
    matches = []
    text_lower = text.lower()
    
    for term in terms:
        term_lower = term.lower()
        start = 0
        while True:
            pos = text_lower.find(term_lower, start)
            if pos == -1:
                break
            
            # Контекст: 50 символов до и после
            ctx_start = max(0, pos - 50)
            ctx_end = min(len(text), pos + len(term) + 50)
            context = text[ctx_start:ctx_end]
            
            matches.append({
                'term': term,
                'position': pos,
                'context': f"...{context}..."
            })
            start = pos + 1
    
    return matches


def process_file(file_path: Path) -> Dict:
    """Обработать один аудиофайл"""
    print(f"\\n📁 Обработка: {file_path.name}")
    print(f"   Размер: {file_path.stat().st_size / 1024:.1f} КБ")
    
    result = {
        'file': file_path.name,
        'text': '',
        'nomenclature_matches': [],
        'status': 'unknown',
    }
    
    try:
        # Конвертация
        print("   ⏳ Конвертация в PCM...")
        try:
            pcm_data = convert_to_pcm(str(file_path))
        except Exception:
            print("   ⏳ Конвертация через ffmpeg subprocess...")
            pcm_data = convert_with_ffmpeg_subprocess(str(file_path))
        
        print(f"   📊 PCM размер: {len(pcm_data) / 1024:.1f} КБ")
        
        # Распознавание
        print("   ⏳ Отправка на распознавание...")
        response = recognize_speech(pcm_data)
        
        text = response.get('result', '')
        result['text'] = text
        result['status'] = 'success'
        
        print(f"   ✅ Распознано: {len(text)} символов")
        if text:
            print(f"   📝 Текст: {text[:100]}{'...' if len(text) > 100 else ''}")
        
        # Поиск номенклатуры
        if NOMENCLATURE and text:
            matches = search_nomenclature(text, NOMENCLATURE)
            result['nomenclature_matches'] = matches
            
            if matches:
                print(f"   🏷️  Найдено совпадений: {len(matches)}")
                for m in matches:
                    print(f"      • \"{m['term']}\" {m['context']}")
            else:
                print("   🏷️  Совпадений номенклатуры не найдено")
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        print(f"   ❌ Ошибка: {e}")
    
    return result


def analyze_audio_info(file_path: Path) -> Dict:
    """Анализ информации об аудиофайле (до распознавания)"""
    info = {
        'file': file_path.name,
        'size_kb': round(file_path.stat().st_size / 1024, 1),
        'format': file_path.suffix.lower(),
    }
    
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(str(file_path))
        info.update({
            'duration_sec': round(len(audio) / 1000, 1),
            'sample_rate': audio.frame_rate,
            'channels': audio.channels,
            'sample_width': audio.sample_width,
            'rms_db': round(audio.rms_dBFS, 1) if audio.rms_dBFS != float('-inf') else -96.0,
            'is_loud': audio.rms_dBFS > -20 if audio.rms_dBFS != float('-inf') else False,
            'is_silent': audio.rms_dBFS < -50 if audio.rms_dBFS != float('-inf') else True,
        })
        
        # Анализ тишины
        silence_count = 0
        chunk_length = 1000  # 1 секунда
        for i in range(0, len(audio), chunk_length):
            chunk = audio[i:i + chunk_length]
            if chunk.dBFS < -40:
                silence_count += 1
        
        total_chunks = len(audio) // chunk_length + 1
        info['silence_ratio'] = round(silence_count / total_chunks * 100, 1)
        
    except Exception as e:
        info['analysis_error'] = str(e)
    
    return info


def print_audio_info(info: Dict):
    """Вывести информацию об аудиофайле"""
    print(f"\\n📊 Анализ файла: {info['file']}")
    print(f"   Формат: {info['format'].upper()} | Размер: {info['size_kb']} КБ")
    
    if 'duration_sec' in info:
        mins = int(info['duration_sec'] // 60)
        secs = int(info['duration_sec'] % 60)
        print(f"   Длительность: {mins}:{secs:02d}")
        print(f"   Sample Rate: {info['sample_rate']} Гц")
        print(f"   Каналы: {info['channels']} | Разрядность: {info['sample_width'] * 8} бит")
        print(f"   Громкость (RMS): {info['rms_db']} дБ")
        
        if info.get('is_silent'):
            print(f"   ⚠️  Файл почти полностью тихий — возможна проблема с записью")
        elif info.get('is_loud'):
            print(f"   🔊 Файл громкий")
        
        if info.get('silence_ratio', 0) > 50:
            print(f"   🔇 {info['silence_ratio']}% файла — тишина (возможно, записано не всё)")
        elif info.get('silence_ratio', 0) > 20:
            print(f"   🔈 {info['silence_ratio']}% файла — паузы")


def main():
    """Главная функция"""
    print("=" * 60)
    print("🎤 Аудио Анализатор — Яндекс SpeechKit")
    print("=" * 60)
    
    # Проверка API ключа
    if API_KEY == 'YOUR_API_KEY_HERE':
        print("\\n❌ Укажите API ключ в переменной API_KEY")
        print("   Получить: https://console.cloud.yandex.ru/")
        return
    
    # Получение файлов
    print(f"\\n📂 Поиск файлов в: {AUDIO_DIR}")
    
    if not os.path.exists(AUDIO_DIR):
        os.makedirs(AUDIO_DIR, exist_ok=True)
        print(f"   Создана директория: {AUDIO_DIR}")
        print(f"   Поместите туда MP3 файлы и запустите снова")
        return
    
    files = get_audio_files(AUDIO_DIR)
    
    if not files:
        print("   ⚠️  Аудиофайлы не найдены!")
        print(f"   Поместите файлы в: {os.path.abspath(AUDIO_DIR)}")
        return
    
    print(f"   Найдено файлов: {len(files)}")
    
    # Предварительный анализ файлов
    print("\\n" + "-" * 40)
    print("📋 ПРЕДВАРИТЕЛЬНЫЙ АНАЛИЗ ФАЙЛОВ")
    print("-" * 40)
    
    audio_infos = []
    for file_path in files:
        info = analyze_audio_info(file_path)
        audio_infos.append(info)
        print_audio_info(info)
    
    # Сохранение анализа
    analysis_file = "audio_analysis.json"
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(audio_infos, f, ensure_ascii=False, indent=2)
    print(f"\\n💾 Анализ сохранён: {analysis_file}")
    
    # Обработка файлов (распознавание)
    print("\\n" + "-" * 40)
    print("🎤 РАСПОЗНАВАНИЕ РЕЧИ")
    print("-" * 40)
    
    all_results = []
    for file_path in files:
        result = process_file(file_path)
        all_results.append(result)
    
    # Итоговая статистика
    print("\\n" + "=" * 60)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 60)
    
    success = [r for r in all_results if r['status'] == 'success']
    errors = [r for r in all_results if r['status'] == 'error']
    
    print(f"   ✅ Успешно: {len(success)}")
    print(f"   ❌ Ошибки: {len(errors)}")
    
    total_matches = sum(len(r['nomenclature_matches']) for r in all_results)
    print(f"   🏷️  Совпадений номенклатуры: {total_matches}")
    
    # Сохранение результатов
    output_file = "recognition_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\\n💾 Результаты сохранены: {output_file}")
    
    # Экспорт текста
    text_file = "recognition_text.txt"
    with open(text_file, 'w', encoding='utf-8') as f:
        for r in all_results:
            f.write(f"=== {r['file']} ===\\n")
            f.write(f"{r['text']}\\n\\n")
    print(f"💾 Текст сохранён: {text_file}")
    
    # Экспорт номенклатуры
    if NOMENCLATURE and total_matches > 0:
        nomenclature_file = "nomenclature_matches.txt"
        with open(nomenclature_file, 'w', encoding='utf-8') as f:
            for r in all_results:
                if r['nomenclature_matches']:
                    f.write(f"=== {r['file']} ===\\n")
                    for m in r['nomenclature_matches']:
                        f.write(f"  [{m['term']}] {m['context']}\\n")
                    f.write("\\n")
        print(f"💾 Номенклатура сохранена: {nomenclature_file}")


if __name__ == '__main__':
    main()
`;

  const handleCopy = () => {
    navigator.clipboard.writeText(script);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Info */}
      <div className="bg-green-500/10 border border-green-500/20 rounded-2xl p-6">
        <h3 className="text-green-300 font-semibold flex items-center gap-2 mb-2">
          <i className="fab fa-python text-xl"></i>
          Python скрипт для обработки файлов
        </h3>
        <p className="text-green-200/80 text-sm mb-3">
          Этот скрипт обрабатывает MP3 файлы локально, конвертирует их в PCM формат
          и отправляет на распознавание через Яндекс SpeechKit API.
        </p>
        <div className="bg-black/20 rounded-xl p-3">
          <p className="text-green-300/80 text-xs font-mono">
            # Установка зависимостей:<br/>
            pip install requests pydub<br/><br/>
            # Также нужен ffmpeg:<br/>
            # macOS: brew install ffmpeg<br/>
            # Ubuntu: sudo apt install ffmpeg<br/>
            # Windows: скачать с ffmpeg.org
          </p>
        </div>
      </div>

      {/* Nomenclature Input */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
          <i className="fas fa-tags text-purple-400"></i>
          Номенклатура для поиска
        </h3>
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={nomenclatureInput}
            onChange={(e) => setNomenclatureInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addTerm()}
            placeholder="Добавить термин..."
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-purple-400/50"
          />
          <button
            onClick={addTerm}
            className="px-4 py-2 rounded-xl bg-purple-500/20 text-purple-300 text-sm font-medium hover:bg-purple-500/30 transition-colors"
          >
            <i className="fas fa-plus"></i>
          </button>
        </div>
        {nomenclatureTerms.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {nomenclatureTerms.map((term) => (
              <span
                key={term}
                className="inline-flex items-center gap-1 bg-purple-500/20 text-purple-300 text-xs px-3 py-1 rounded-full"
              >
                {term}
                <button onClick={() => removeTerm(term)} className="hover:text-white">
                  <i className="fas fa-xmark text-[10px]"></i>
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Script Output */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <span className="text-gray-300 text-sm font-medium flex items-center gap-2">
            <i className="fab fa-python text-yellow-400"></i>
            audio_analyzer.py
          </span>
          <button
            onClick={handleCopy}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
              copied
                ? 'bg-green-500/20 text-green-300'
                : 'bg-white/10 text-gray-300 hover:bg-white/20'
            }`}
          >
            {copied ? (
              <><i className="fas fa-check mr-1"></i>Скопировано</>
            ) : (
              <><i className="fas fa-copy mr-1"></i>Копировать</>
            )}
          </button>
        </div>
        <pre className="p-4 text-xs text-gray-300 overflow-x-auto max-h-[600px] overflow-y-auto font-mono leading-relaxed">
          {script}
        </pre>
      </div>
    </div>
  );
}
