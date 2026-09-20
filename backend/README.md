# Бэкенд аудио-анализатора

Flask-сервер для распознавания речи из MP3 файлов через Яндекс SpeechKit.

## Зачем нужен бэкенд?

Яндекс SpeechKit API не поддерживает CORS — прямые запросы из браузера блокируются.
Этот сервер принимает файлы от фронтенда, конвертирует их в нужный формат и отправляет в SpeechKit.

## Установка

```bash
# 1. Перейти в папку backend
cd backend

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Установить ffmpeg (для конвертации MP3)
# macOS:
brew install ffmpeg
# Ubuntu/Debian:
sudo apt install ffmpeg
# Windows: скачать с https://ffmpeg.org/download.html и добавить в PATH
```

## Запуск

```bash
python server.py
```

Сервер запустится на `http://localhost:5000`

## Endpoints

### GET /health
Проверка работоспособности.

```bash
curl http://localhost:5000/health
```

### POST /recognize
Распознавание речи.

```bash
curl -X POST http://localhost:5000/recognize \
  -F "file=@audio.mp3" \
  -F "api_key=YOUR_API_KEY" \
  -F "folder_id=b1g..." \
  -F "language=ru-RU" \
  -F "model=general" \
  -F 'nomenclature=["артикул","серийный номер"]'
```

**Параметры:**
- `file` — аудиофайл (MP3, WAV, OGG, M4A, FLAC)
- `api_key` — API-ключ Яндекс SpeechKit (обязательно)
- `folder_id` — Folder ID (опционально)
- `language` — язык: ru-RU, en-US, tr-TR (по умолчанию ru-RU)
- `model` — модель: general, general:rc, maps, dates, names, numbers (по умолчанию general)
- `nomenclature` — JSON-массив терминов для поиска в тексте (опционально)

**Ответ:**
```json
{
  "text": "распознанный текст...",
  "confidence": 0.95,
  "audio_info": {
    "duration_sec": 12.3,
    "sample_rate": 44100,
    "channels": 2,
    "rms_dbfs": -18.5
  },
  "pcm_size": 393600,
  "nomenclature_matches": [
    {
      "term": "артикул",
      "position": 42,
      "context": "...товар имеет артикул 12345..."
    }
  ]
}
```

### POST /analyze
Анализ аудиофайла без распознавания.

```bash
curl -X POST http://localhost:5000/analyze \
  -F "file=@audio.mp3"
```

## Как это работает

1. **Принимает** MP3 файл от фронтенда
2. **Анализирует** параметры (длительность, громкость, каналы)
3. **Конвертирует** в PCM 16kHz mono 16bit (требование SpeechKit)
4. **Отправляет** в SpeechKit API
5. **Возвращает** распознанный текст + поиск номенклатуры

## Решение проблем

### `FileNotFoundError: ffmpeg`
Установите ffmpeg и добавьте в PATH. Перезапустите терминал.

### `ModuleNotFoundError: flask`
```bash
pip install -r requirements.txt
```

### Пустой текст при распознавании
- Проверьте, что в файле есть речь
- Убедитесь что громкость нормальная (не тише -40 dBFS)
- Проверьте что язык указан верно

### CORS ошибки на фронтенде
Убедитесь что сервер запущен и фронтенд обращается к `http://localhost:5000`
