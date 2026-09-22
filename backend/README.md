# Backend - Аудио анализатор и импорт данных

Flask сервер для:
1. Распознавания речи из MP3 через Яндекс SpeechKit
2. Импорта данных из XLSX файлов (номенклатура, клиенты)

## Возможности

### 🎤 Распознавание речи
- Загрузка MP3 файлов
- Конвертация в PCM 16kHz mono
- Отправка в Яндекс SpeechKit API
- Получение распознанного текста

### 📊 Анализ XLSX
- Анализ структуры Excel файлов
- Определение типов данных
- Подсчёт заполненных ячеек
- Примеры значений

### 📦 Импорт номенклатуры
- Импорт из XLSX файлов
- Валидация данных
- Сохранение в JSON
- Статистика по полям

### 👥 Импорт клиентов
- Импорт из XLSX файлов
- Валидация данных
- Сохранение в JSON
- Статистика по полям

## Быстрый старт

### 1. Установка зависимостей

```bash
cd backend
pip install -r requirements.txt
```

### 2. Запуск сервера

```bash
python server.py
```

Сервер запустится на `http://localhost:5000`

### 3. Импорт данных

```bash
# Анализ XLSX файла
python analyze_xlsx.py file.xlsx

# Импорт номенклатуры
python import_nomenclature.py nomenclature.xlsx

# Импорт клиентов
python import_clients.py clients.xlsx

# Импорт обоих файлов
python import_all.py nomenclature.xlsx clients.xlsx
```

## API Endpoints

### GET /health
Проверка работоспособности сервера.

```bash
curl http://localhost:5000/health
```

### POST /recognize
Распознавание речи из аудиофайла.

```bash
curl -X POST http://localhost:5000/recognize \
  -F "file=@audio.mp3" \
  -F "api_key=YOUR_API_KEY" \
  -F "language=ru-RU" \
  -F "model=general"
```

**Параметры:**
- `file` - аудиофайл (MP3, WAV, OGG, M4A, FLAC)
- `api_key` - API-ключ Яндекс SpeechKit (обязательно)
- `folder_id` - Folder ID (опционально)
- `language` - язык: ru-RU, en-US, tr-TR (по умолчанию ru-RU)
- `model` - модель: general, general:rc, maps, dates, names, numbers (по умолчанию general)

**Ответ:**
```json
{
  "text": "распознанный текст",
  "confidence": 0.95,
  "audio_info": {
    "duration_sec": 12.3,
    "sample_rate": 44100,
    "channels": 2,
    "rms_dbfs": -18.5
  },
  "pcm_size": 393600
}
```

### POST /analyze
Анализ аудиофайла без распознавания.

```bash
curl -X POST http://localhost:5000/analyze \
  -F "file=@audio.mp3"
```

### POST /analyze-xlsx
Анализ XLSX файла.

```bash
curl -X POST http://localhost:5000/analyze-xlsx \
  -F "file=@nomenclature.xlsx"
```

**Ответ:**
```json
{
  "file": "nomenclature.xlsx",
  "file_size_mb": 0.03,
  "sheets": [
    {
      "name": "Лист_1",
      "max_row": 318,
      "max_column": 11,
      "columns": [
        {
          "letter": "A",
          "header": "Наименование",
          "type": "string",
          "non_empty_count": 315,
          "sample_values": ["Товар 1", "Товар 2", "Товар 3"]
        }
      ],
      "sample_rows": [...]
    }
  ]
}
```

## Структура файлов

### Номенклатура

Файл: `ЦыганковНоменклатура.xlsx`
- 318 строк × 11 колонок
- Обязательные поля: Наименование
- Результат: `ЦыганковНоменклатура.import.json`

### Клиенты

Файл: `Клиенты.xlsx`
- 131 строка × 23 колонки
- Обязательные поля: Наименование
- Результат: `Клиенты.import.json`

## Docker

### Запуск

```bash
docker compose up -d backend
```

### Вход в контейнер

```bash
docker compose exec backend bash
```

### Импорт данных

```bash
docker compose exec backend python import_all.py /app/data/nomenclature.xlsx /app/data/clients.xlsx
```

## Логирование

Все скрипты выводят подробные логи:

```
======================================================================
📦 ИМПОРТ НОМЕНКЛАТУРЫ
======================================================================
📁 Файл: ЦыганковНоменклатура.xlsx
📖 Загружаем workbook...
📄 Лист: Лист_1
📋 Найдено колонок: 11

🔄 Импортируем данные...
✅ Прочитано строк: 318

🔍 Валидация данных...
✅ Валидных: 315
❌ Ошибок: 3

💾 Результаты сохранены: ЦыганковНоменклатура.import.json

======================================================================
✅ ИМПОРТ ЗАВЕРШЁН
======================================================================
```

## Документация

- [IMPORT_GUIDE.md](IMPORT_GUIDE.md) - Полное руководство по импорту
- [IMPORT_NOMENCLATURE.md](IMPORT_NOMENCLATURE.md) - Импортер номенклатуры
- [IMPORT_CLIENTS.md](IMPORT_CLIENTS.md) - Импортер клиентов
- [XLSX_IMPORT_README.md](XLSX_IMPORT_README.md) - Анализ XLSX файлов
- [DEBUG_LOGGING.md](../DEBUG_LOGGING.md) - Логирование и отладка

## Зависимости

```txt
flask>=3.0.0
flask-cors>=4.0.0
requests>=2.31.0
pydub>=0.25.1
openpyxl>=3.1.0
```

## Решение проблем

### Ошибка: ffmpeg не найден
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Скачать с https://ffmpeg.org/download.html
```

### Ошибка: openpyxl не установлен
```bash
pip install openpyxl
```

### Ошибка: CORS
Убедитесь что в `server.py` есть:
```python
from flask_cors import CORS
CORS(app)
```

### Ошибка при импорте
1. Проверьте структуру XLSX файла через `analyze_xlsx.py`
2. Проверьте логи в консоли
3. Убедитесь что все обязательные поля заполнены
4. Проверьте права доступа к файлам

## Поддержка

Если возникли проблемы:
1. Проверьте логи в консоли
2. Проверьте структуру XLSX файла
3. Убедитесь что все зависимости установлены
4. Пришлите ошибку и структуру файла
