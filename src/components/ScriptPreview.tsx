import { useState, useMemo } from 'react';
import type { AppConfig } from '../types';

interface Props {
  config: AppConfig;
}

function generateScript(config: AppConfig): string {
  const termsStr = config.nomenclatureTerms.length > 0
    ? config.nomenclatureTerms.map(t => `    "${t}"`).join(',\n')
    : '    # Добавьте свои термины\n    # "артикул",\n    # "серийный номер"';

  return `#!/usr/bin/env python3
"""
MP3 → Текст → Номенклатура
Распознавание речи из MP3 файлов через Яндекс SpeechKit
и поиск специфичной номенклатуры в распознанном тексте.

Сгенерировано автоматически. Настройте параметры ниже.
"""

import os
import sys
import json
import csv
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# ==================== НАСТРОЙКИ ====================

API_KEY = "${config.apiKey || 'YOUR_API_KEY_HERE'}"
FOLDER_ID = "${config.folderId || ''}"
AUDIO_DIR = "${config.audioDir}"
OUTPUT_DIR = "${config.outputDir}"
LANGUAGE = "${config.language}"
MODEL = "${config.model}"

# Номенклатура для поиска в распознанном тексте
NOMENCLATURE = [
${termsStr}
]

# Нечёткий поиск
USE_FUZZY = ${config.useFuzzySearch}
FUZZY_THRESHOLD = ${config.fuzzyThreshold}

# ==================== ЗАВИСИМОСТИ ====================
# pip install requests pydub rapidfuzz
# Также нужен ffmpeg (https://ffmpeg.org/)

try:
    from pydub import AudioSegment
except ImportError:
    print("❌ Установите pydub: pip install pydub")
    sys.exit(1)

try:
    from rapidfuzz import fuzz
except ImportError:
    if USE_FUZZY:
        print("⚠️  rapidfuzz не установлен. Нечёткий поиск отключён.")
        print("   Установите: pip install rapidfuzz")
        USE_FUZZY = False

# ==================== ФУНКЦИИ ====================


def get_audio_files(directory: str) -> List[Path]:
    """Получить список аудиофайлов"""
    audio_dir = Path(directory)
    if not audio_dir.exists():
        return []
    extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac', '.wma'}
    return sorted([f for f in audio_dir.iterdir() if f.suffix.lower() in extensions])


def analyze_audio(file_path: Path) -> Dict:
    """Анализ параметров аудиофайла"""
    try:
        audio = AudioSegment.from_file(str(file_path))
        duration_sec = len(audio) / 1000
        
        # Анализ тишины (по секундам)
        silence_chunks = 0
        total_chunks = 0
        chunk_ms = 1000
        for i in range(0, len(audio), chunk_ms):
            chunk = audio[i:i + chunk_ms]
            total_chunks += 1
            if chunk.dBFS < -40:
                silence_chunks += 1
        
        silence_ratio = (silence_chunks / total_chunks * 100) if total_chunks > 0 else 0
        
        return {
            'duration_sec': round(duration_sec, 1),
            'sample_rate': audio.frame_rate,
            'channels': audio.channels,
            'rms_dbfs': round(audio.dBFS, 1),
            'silence_ratio': round(silence_ratio, 1),
            'is_silent': audio.dBFS < -50,
        }
    except Exception as e:
        return {'error': str(e)}


def convert_to_pcm(file_path: Path) -> bytes:
    """Конвертировать аудио в PCM 16kHz mono 16bit для SpeechKit"""
    audio = AudioSegment.from_file(str(file_path))
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    return audio.raw_data


def recognize_speech(pcm_data: bytes) -> Dict:
    """Отправить аудио на распознавание в Яндекс SpeechKit"""
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    
    params = {
        'topic': MODEL,
        'lang': LANGUAGE,
        'format': 'lpcm',
        'sampleRateHertz': '16000',
    }
    
    if FOLDER_ID:
        params['folderId'] = FOLDER_ID
    
    headers = {
        'Authorization': f'Api-Key {API_KEY}',
    }
    
    response = requests.post(url, params=params, headers=headers, data=pcm_data)
    
    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: {response.text}")
    
    return response.json()


def search_nomenclature_exact(text: str, terms: List[str]) -> List[Dict]:
    """Точный поиск номенклатуры"""
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
                'type': 'exact',
            })
            start = pos + 1
    
    return matches


def search_nomenclature_fuzzy(text: str, terms: List[str], threshold: float) -> List[Dict]:
    """Нечёткий поиск номенклатуры (учитывает ошибки распознавания)"""
    matches = []
    words = text.lower().split()
    
    for term in terms:
        term_words = term.lower().split()
        term_len = len(term_words)
        
        for i in range(len(words)):
            # Проверяем окно из term_len слов
            window = words[i:i + term_len]
            if len(window) < term_len:
                continue
            
            window_text = ' '.join(window)
            score = fuzz.ratio(term.lower(), window_text) / 100.0
            
            if score >= threshold:
                # Находим позицию в оригинальном тексте
                pos = text.lower().find(window_text)
                if pos == -1:
                    continue
                
                ctx_start = max(0, pos - 50)
                ctx_end = min(len(text), pos + len(window_text) + 50)
                
                matches.append({
                    'term': term,
                    'found_as': window_text,
                    'score': round(score, 2),
                    'position': pos,
                    'context': text[ctx_start:ctx_end].strip(),
                    'type': 'fuzzy',
                })
    
    return matches


def search_nomenclature(text: str, terms: List[str]) -> List[Dict]:
    """Поиск номенклатуры (точный + нечёткий)"""
    exact = search_nomenclature_exact(text, terms)
    
    if USE_FUZZY:
        fuzzy = search_nomenclature_fuzzy(text, terms, FUZZY_THRESHOLD)
        # Убираем дубликаты (если точное совпадение уже есть)
        exact_positions = {m['position'] for m in exact}
        fuzzy = [m for m in fuzzy if m['position'] not in exact_positions]
        return exact + fuzzy
    
    return exact


def process_file(file_path: Path) -> Dict:
    """Обработать один аудиофайл"""
    print(f"\\n{'='*50}")
    print(f"📁 {file_path.name}")
    print(f"{'='*50}")
    
    result = {
        'file': file_path.name,
        'file_path': str(file_path),
        'text': '',
        'nomenclature_matches': [],
        'audio_info': {},
        'status': 'unknown',
        'processing_time': 0,
    }
    
    start_time = time.time()
    
    try:
        # 1. Анализ аудио
        print("  📊 Анализ файла...")
        result['audio_info'] = analyze_audio(file_path)
        
        if 'error' in result['audio_info']:
            print(f"  ⚠️  Ошибка анализа: {result['audio_info']['error']}")
        else:
            info = result['audio_info']
            print(f"  ⏱️  Длительность: {info['duration_sec']}с")
            print(f"  🔊 Громкость: {info['rms_dbfs']} dBFS")
            print(f"  🔇 Тишина: {info['silence_ratio']}%")
            
            if info.get('is_silent'):
                print("  ⚠️  Файл очень тихий — возможны проблемы с распознаванием")
        
        # 2. Конвертация
        print("  🔄 Конвертация в PCM 16kHz...")
        pcm_data = convert_to_pcm(file_path)
        print(f"  📦 PCM: {len(pcm_data) / 1024:.0f} КБ")
        
        # 3. Распознавание
        print("  🎤 Отправка на распознавание...")
        response = recognize_speech(pcm_data)
        
        text = response.get('result', '')
        result['text'] = text
        result['status'] = 'success'
        
        if text:
            print(f"  ✅ Распознано: {len(text)} символов")
            preview = text[:80] + ('...' if len(text) > 80 else '')
            print(f"  📝 \"{preview}\"")
        else:
            print("  ⚠️  Текст не распознан (возможно, нет речи)")
        
        # 4. Поиск номенклатуры
        if NOMENCLATURE and text:
            matches = search_nomenclature(text, NOMENCLATURE)
            result['nomenclature_matches'] = matches
            
            if matches:
                print(f"  🏷️  Найдено совпадений: {len(matches)}")
                for m in matches[:5]:  # Показываем первые 5
                    score_str = f" ({m['score']:.0%})" if 'score' in m else ""
                    print(f"     • \"{m['term']}\"{score_str}: ...{m['context'][:60]}...")
                if len(matches) > 5:
                    print(f"     ... и ещё {len(matches) - 5}")
            else:
                print("  🏷️  Совпадений не найдено")
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        print(f"  ❌ Ошибка: {e}")
    
    result['processing_time'] = round(time.time() - start_time, 1)
    print(f"  ⏱️  Время: {result['processing_time']}с")
    
    return result


def save_results(results: List[Dict], output_dir: str):
    """Сохранить результаты в файлы"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    # JSON
    json_path = out / 'results.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"💾 JSON: {json_path}")
    
    # TXT
    txt_path = out / 'results.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(f"{'='*60}\\n")
            f.write(f"Файл: {r['file']}\\n")
            f.write(f"Статус: {r['status']}\\n")
            if r.get('processing_time'):
                f.write(f"Время обработки: {r['processing_time']}с\\n")
            f.write(f"{'='*60}\\n\\n")
            f.write(f"{r['text']}\\n\\n")
            if r['nomenclature_matches']:
                f.write(f"--- Номенклатура ---\\n")
                for m in r['nomenclature_matches']:
                    f.write(f"  [{m['term']}] {m['context']}\\n")
                f.write("\\n")
    print(f"💾 TXT: {txt_path}")
    
    # CSV
    csv_path = out / 'nomenclature_matches.csv'
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Файл', 'Термин', 'Найдено как', 'Совпадение', 'Контекст'])
        for r in results:
            for m in r['nomenclature_matches']:
                writer.writerow([
                    r['file'],
                    m['term'],
                    m.get('found_as', m['term']),
                    m.get('score', 1.0),
                    m['context'],
                ])
    print(f"💾 CSV: {csv_path}")


def main():
    print("╔══════════════════════════════════════════╗")
    print("║  🎤 MP3 → Текст → Номенклатура          ║")
    print("║  Яндекс SpeechKit Recognition Tool       ║")
    print("╚══════════════════════════════════════════╝")
    
    # Проверки
    if API_KEY == 'YOUR_API_KEY_HERE':
        print("\\n❌ Укажите API_KEY!")
        print("   Получить: https://console.cloud.yandex.ru/")
        sys.exit(1)
    
    if not NOMENCLATURE:
        print("\\n⚠️  Список номенклатуры пуст!")
        print("   Добавьте термины в переменную NOMENCLATURE")
    
    # Поиск файлов
    print(f"\\n📂 Папка: {AUDIO_DIR}")
    files = get_audio_files(AUDIO_DIR)
    
    if not files:
        print("❌ Файлы не найдены!")
        print(f"   Положите MP3 в: {os.path.abspath(AUDIO_DIR)}")
        sys.exit(1)
    
    print(f"   Найдено: {len(files)} файл(ов)")
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"     • {f.name} ({size_kb:.0f} КБ)")
    
    # Обработка
    results = []
    for i, file_path in enumerate(files, 1):
        print(f"\\n[{i}/{len(files)}]", end="")
        result = process_file(file_path)
        results.append(result)
    
    # Статистика
    print("\\n\\n" + "╔══════════════════════════════════════════╗")
    print("║  📊 ИТОГИ                                 ║")
    print("╚══════════════════════════════════════════╝")
    
    success = [r for r in results if r['status'] == 'success']
    errors = [r for r in results if r['status'] == 'error']
    total_matches = sum(len(r['nomenclature_matches']) for r in results)
    total_time = sum(r.get('processing_time', 0) for r in results)
    
    print(f"  ✅ Успешно: {len(success)}/{len(results)}")
    print(f"  ❌ Ошибки: {len(errors)}")
    print(f"  🏷️  Совпадений номенклатуры: {total_matches}")
    print(f"  ⏱️  Общее время: {total_time:.1f}с")
    
    # Сохранение
    print(f"\\n💾 Сохранение в: {OUTPUT_DIR}")
    save_results(results, OUTPUT_DIR)
    
    print("\\n🎉 Готово!")


if __name__ == '__main__':
    main()
`;
}

export default function ScriptPreview({ config }: Props) {
  const [copied, setCopied] = useState(false);

  const script = useMemo(() => generateScript(config), [config]);

  const handleCopy = () => {
    navigator.clipboard.writeText(script);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([script], { type: 'text/x-python' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'mp3_recognizer.py';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const hasApiKey = config.apiKey && config.apiKey !== '';
  const hasTerms = config.nomenclatureTerms.length > 0;

  return (
    <div className="space-y-6">
      {/* Status */}
      <div className={`rounded-2xl border p-4 ${
        hasApiKey && hasTerms
          ? 'bg-green-500/10 border-green-500/20'
          : 'bg-red-500/10 border-red-500/20'
      }`}>
        <div className="flex items-center gap-2 mb-2">
          <i className={`fas ${hasApiKey && hasTerms ? 'fa-check-circle text-green-400' : 'fa-exclamation-circle text-red-400'}`}></i>
          <span className={`font-medium ${hasApiKey && hasTerms ? 'text-green-300' : 'text-red-300'}`}>
            {hasApiKey && hasTerms ? 'Скрипт готов к скачиванию' : 'Заполните обязательные поля'}
          </span>
        </div>
        <ul className="text-sm space-y-1">
          <li className={hasApiKey ? 'text-green-300/70' : 'text-red-300/70'}>
            {hasApiKey ? '✅' : '❌'} API-ключ {hasApiKey ? 'указан' : 'не указан'}
          </li>
          <li className={hasTerms ? 'text-green-300/70' : 'text-yellow-300/70'}>
            {hasTerms ? '✅' : '⚠️'} Номенклатура: {config.nomenclatureTerms.length} терм(ов)
            {!hasTerms && ' (можно добавить позже в скрипте)'}
          </li>
        </ul>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={handleDownload}
          className="flex-1 py-3 rounded-xl bg-gradient-to-r from-green-500/20 to-emerald-500/20 border border-green-500/30 text-green-300 font-medium hover:from-green-500/30 hover:to-emerald-500/30 transition-all flex items-center justify-center gap-2"
        >
          <i className="fas fa-download"></i>
          Скачать mp3_recognizer.py
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
            mp3_recognizer.py
          </span>
          <span className="text-gray-500 text-xs">
            {script.split('\n').length} строк
          </span>
        </div>
        <pre className="p-4 text-xs text-gray-300 overflow-x-auto max-h-[600px] overflow-y-auto font-mono leading-relaxed">
          {script}
        </pre>
      </div>
    </div>
  );
}
