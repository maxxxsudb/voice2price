# Итоговая сводка проекта

## Что сделано

### ✅ Фронтенд (React + TypeScript)
- Загрузка MP3 файлов с drag-n-drop
- Предварительный анализ аудио (waveform, длительность)
- Настройки API (ключ, язык, модель)
- Результаты распознавания с копированием
- Поиск номенклатуры в тексте
- Анализ XLSX файлов
- Индикатор статуса бэкенда
- Подробное логирование

### ✅ Бэкенд (Python + Flask)
- Распознавание речи через Яндекс SpeechKit
- Конвертация аудио в PCM 16kHz mono
- Анализ XLSX файлов
- Импорт номенклатуры из XLSX
- Импорт клиентов из XLSX
- Подробное логирование
- CORS поддержка

### ✅ Docker
- `Dockerfile` для фронта (node:24-slim)
- `backend/Dockerfile` для бэка (python:3.11-slim + ffmpeg)
- `docker-compose.yml` с пробросом файлов
- Hot-reload для обоих сервисов
- Переменные окружения через `.env`

### ✅ Документация
- `README.md` - главное руководство
- `backend/README.md` - документация бэкенда
- `backend/IMPORT_GUIDE.md` - полное руководство по импорту
- `backend/IMPORT_NOMENCLATURE.md` - импортер номенклатуры
- `backend/IMPORT_CLIENTS.md` - импортер клиентов
- `backend/XLSX_IMPORT_README.md` - анализ XLSX
- `DEBUG_LOGGING.md` - логирование и отладка
- `FIX_SCREEN_DISAPPEAR.md` - решение проблем с экраном
- `HOW_TO_USE_XLSX_ANALYZER.md` - использование анализатора

## Структура проекта

```
.
├── src/                          # Frontend
│   ├── App.tsx                   # Главный компонент
│   ├── main.tsx                  # Точка входа
│   ├── index.css                 # Стили
│   ├── types.ts                  # Типы
│   └── components/
│       ├── FileUploader.tsx      # Загрузка файлов
│       ├── ApiSettings.tsx       # Настройки API
│       ├── RecognitionResults.tsx # Результаты
│       ├── AudioAnalyzer.tsx     # Анализ аудио
│       ├── NomenclatureSearch.tsx # Поиск номенклатуры
│       ├── XlsxAnalyzer.tsx      # Анализ XLSX
│       └── PythonScriptGenerator.tsx # Генератор скриптов
│
├── backend/                      # Backend
│   ├── server.py                 # Flask сервер
│   ├── analyze_xlsx.py           # Анализ XLSX
│   ├── import_nomenclature.py    # Импорт номенклатуры
│   ├── import_clients.py         # Импорт клиентов
│   ├── import_all.py             # Главный скрипт импорта
│   ├── requirements.txt          # Зависимости
│   ├── Dockerfile                # Docker для бэка
│   └── *.md                      # Документация
│
├── Dockerfile                    # Docker для фронта
├── docker-compose.yml            # Оркестрация
├── .env                          # Переменные окружения
├── .dockerignore                 # Исключения Docker
├── vite.config.js                # Конфигурация Vite
├── package.json                  # Зависимости Node.js
└── README.md                     # Главное руководство
```

## Как запустить

### 1. Клонировать проект
```bash
git clone <repository-url>
cd project
```

### 2. Получить API-ключ Яндекс SpeechKit
1. Перейти на https://console.cloud.yandex.ru/
2. Создать сервисный аккаунт с ролью `editor`
3. Создать API-ключ

### 3. Запустить через Docker
```bash
docker compose up --build
```

### 4. Открыть приложение
- **Фронтенд:** http://localhost:3000
- **Бэкенд:** http://localhost:5000

### 5. Использовать

#### Распознавание речи
1. Перейти в "Настройки API" → ввести API-ключ
2. Загрузить MP3 файлы
3. Нажать "Распознать речь"
4. Результаты появятся во вкладке "Результаты"

#### Импорт данных
```bash
# Войти в контейнер
docker compose exec backend bash

# Анализ XLSX
python analyze_xlsx.py file.xlsx

# Импорт номенклатуры
python import_nomenclature.py nomenclature.xlsx

# Импорт клиентов
python import_clients.py clients.xlsx

# Импорт обоих файлов
python import_all.py nomenclature.xlsx clients.xlsx
```

## Структура данных

### Номенклатура (318 строк × 11 колонок)
- Наименование (обязательно)
- Артикул
- Единица измерения веса
- Вес (знаменатель)
- Вес
- Вес (числитель)
- Вид номенклатуры
- Единица для отчетов
- Единица хранения
- GTIN
- Код

### Клиенты (131 строка × 23 колонки)
- Наименование (обязательно)
- Код
- Бизнес-регион
- Дата регистрации
- Клиент
- Комментарий
- Поставщик
- Публичное наименование
- Основной менеджер
- Прочие отношения
- Обслуживается торговыми представителями
- Прочая информация
- Перевозчик
- Шаблон этикетки
- Юр/Физлицо
- Пол
- Дата рождения
- Вариант отправки электронного чека
- Зона доставки
- Вид цен
- Индивидуальный вид цены
- Водитель
- Ак флаг спец цена

## Результаты импорта

После импорта создаются файлы:
- `ЦыганковНоменклатура.import.json` - импортированная номенклатура
- `Клиенты.import.json` - импортированные клиенты

Структура JSON:
```json
{
  "file": "file.xlsx",
  "file_size_mb": 0.03,
  "sheet_name": "Лист_1",
  "total_rows": 318,
  "valid_rows": 315,
  "invalid_rows": 3,
  "items": [...],
  "import_time": "2026-09-22T07:15:30.123456"
}
```

## Логи

### Бэкенд
```bash
docker compose logs -f backend
```

### Фронтенд
Откройте консоль браузера (F12 → Console)

## Решение проблем

### Экран пропадает
1. Проверьте логи бэкенда: `docker compose logs -f backend`
2. Проверьте консоль браузера (F12)
3. Нажмите кнопку "Сырой JSON" на странице
4. См. `FIX_SCREEN_DISAPPEAR.md`

### Ошибки импорта
1. Проверьте структуру XLSX через `analyze_xlsx.py`
2. Проверьте обязательные поля
3. Исправьте ошибки в исходном файле
4. Запустите импорт снова

### Бэкенд не запускается
```bash
docker compose down
docker compose up --build
```

## Следующие шаги

1. ✅ Проверить файлы `.import.json`
2. ✅ Исправить ошибки валидации
3. ⏳ Загрузить данные в базу данных
4. ⏳ Настроить связи между номенклатурой и клиентами
5. ⏳ Создать API для доступа к данным
6. ⏳ Добавить веб-интерфейс для управления данными

## Полезные команды

```bash
# Запустить
docker compose up

# Перезапустить
docker compose restart

# Остановить
docker compose down

# Логи
docker compose logs -f

# Войти в контейнер
docker compose exec backend bash

# Проверить здоровье
curl http://localhost:5000/health

# Анализ XLSX
curl -X POST http://localhost:5000/analyze-xlsx -F "file=@file.xlsx"

# Распознавание речи
curl -X POST http://localhost:5000/recognize \
  -F "file=@audio.mp3" \
  -F "api_key=YOUR_KEY"
```

## Зависимости

### Frontend
- React 18
- TypeScript
- Vite
- Tailwind CSS
- Font Awesome

### Backend
- Flask
- Flask-CORS
- requests
- pydub
- openpyxl

### Docker
- Node 24 slim
- Python 3.11 slim
- ffmpeg

## Лицензия

MIT

## Поддержка

Если возникли проблемы:
1. Проверьте логи
2. Проверьте документацию
3. Пришлите ошибку и контекст
