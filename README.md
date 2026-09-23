# Аудио Анализатор — Docker Compose

Полноценное приложение для распознавания речи из MP3 файлов через Яндекс SpeechKit с поиском номенклатуры.

## Быстрый старт

### 1. Запустить через Docker Compose

```bash
# Запустить все сервисы (фронт + бэк + БД)
# Важно: --build пересобирает образы с последними изменениями кода
docker compose up --build

# Или в фоне
docker compose up -d --build
```

> **Важно:** Флаг `--build` обязателен при первом запуске после `git pull`, чтобы применить последние изменения кода в контейнерах. Без него Docker может использовать закэшированные образы.

> **Инициализация БД:** При первом запуске скрипт инициализации автоматически создаст все необходимые таблицы в базе данных. Дождитесь сообщения "✅ Инициализация завершена" в логах бэкенда.

### 2. Открыть приложение

- **Фронтенд:** http://localhost:3000
- **Бэкенд:** http://localhost:5000

### 3. Настроить Яндекс Облако

1. Перейти на [console.cloud.yandex.ru](https://console.cloud.yandex.ru/)
2. Создать сервисный аккаунт с ролью `editor`
3. Создать ключ в формате JSON
4. Скачать JSON-файл с ключом

### 4. Настроить интеграцию с Яндекс Облаком

1. В интерфейсе перейти во вкладку **"Настройки Яндекс Облака"**
2. Вставить JSON-ключ сервисного аккаунта (или только приватный ключ в PEM-формате)
3. Указать Folder ID (начинается с `b1g`)
4. Нажать **"Сохранить и протестировать"**

> **Важно:** При вставке приватного ключа в PEM-формате нажмите кнопку **"Показать"**, чтобы видеть содержимое поля.

### 5. Использование

В интерфейсе:
1. Перейти в **"Аудио анализатор"** → загрузить MP3 файлы
2. Нажать **"Распознать речь"**
3. Результаты появятся во вкладке **"Результаты"**
4. Добавить термины номенклатуры во вкладке **"Номенклатура"**

## Архитектура

```
┌─────────────────────┐         ┌─────────────────────┐         ┌─────────────────┐
│   Frontend (React)  │  HTTP   │   Backend (Flask)   │  HTTPS  │  Яндекс SpeechKit│
│   Node 24 slim      │ ──────▶ │   Python 3.11 slim  │ ──────▶ │   API           │
│   Port: 3000        │         │   Port: 5000        │         │                 │
│                     │         │   + ffmpeg          │         │                 │
└─────────────────────┘         └─────────────────────┘         └─────────────────┘
```

## Разработка с Docker

### Hot-reload

Оба сервиса настроены на автоматическую перезагрузку при изменении кода:

```bash
# Запустить в режиме разработки
docker compose up

# Изменения в src/ автоматически подхватываются Vite
# Изменения в backend/ автоматически подхватываются Flask
```

### Логи

```bash
# Все логи
docker compose logs -f

# Только фронт
docker compose logs -f frontend

# Только бэк
docker compose logs -f backend
```

### Перезапуск

```bash
# Перезапустить после изменений в Dockerfile
docker compose down
docker compose up --build

# Перезапустить только один сервис
docker compose restart frontend
docker compose restart backend
```

### Остановка

```bash
docker compose down
```

## Структура проекта

```
.
├── src/                    # Frontend (React + Vite)
│   ├── components/
│   ├── App.tsx
│   └── ...
├── backend/                # Backend (Flask + Python)
│   ├── server.py
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml      # Оркестрация контейнеров
├── Dockerfile              # Frontend Dockerfile
├── .env                    # Переменные окружения
└── README.md
```

## Docker Compose детали

### Frontend (Node 24 slim)

- **Образ:** `node:24-slim`
- **Порт:** 3000
- **Volume:** проброс исходников для hot-reload
- **Переменные:**
  - `VITE_BACKEND_URL` — URL бэкенда (по умолчанию `http://localhost:5000`)

### Backend (Python 3.11 slim + ffmpeg)

- **Образ:** `python:3.11-slim` + `ffmpeg`
- **Порт:** 5000
- **Volume:** проброс `backend/` для hot-reload
- **Зависимости:** Flask, pydub, requests

### Volumes

```yaml
volumes:
  - .:/app              # Проброс исходников фронта
  - /app/node_modules   # Anonymous volume для node_modules
  - ./backend:/app      # Проброс кода бэка (в сервисе backend)
```

## Команды Docker

```bash
# Запустить
docker compose up

# Запустить в фоне
docker compose up -d

# Пересобрать после изменений
docker compose up --build

# Остановить
docker compose down

# Остановить и удалить volumes
docker compose down -v

# Посмотреть логи
docker compose logs -f

# Логи только фронта
docker compose logs -f frontend

# Логи только бэка
docker compose logs -f backend

# Войти в контейнер фронта
docker compose exec frontend sh

# Войти в контейнер бэка
docker compose exec backend bash
```

## Разработка

### Hot-reload

Оба сервиса настроены на hot-reload:
- **Фронт:** изменения в `src/` автоматически перезагружают Vite
- **Бэк:** изменения в `backend/` автоматически перезагружают Flask

### Изменение порта бэкенда

Если нужно запустить бэкенд на другом порту:

1. В `docker-compose.yml` изменить:
   ```yaml
   backend:
     ports:
       - "8000:5000"  # Внешний порт 8000
   ```

2. В `.env` изменить:
   ```
   VITE_BACKEND_URL=http://localhost:8000
   ```

3. Перезапустить:
   ```bash
   docker compose down
   docker compose up --build
   ```

### Production build

Для production можно использовать multi-stage build:

```dockerfile
# Frontend Dockerfile.production
FROM node:24-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Анализ XLSX файлов

Для импорта номенклатуры и клиентов из Excel файлов:

1. Перейдите на вкладку **"XLSX импорт"**
2. Загрузите XLSX файл
3. Изучите структуру данных
4. Скопируйте результат для генерации импортера

Подробнее: [backend/XLSX_IMPORT_README.md](backend/XLSX_IMPORT_README.md)

## Решение проблем

### Порт 3000 или 5000 занят

Измените порты в `docker-compose.yml`:
```yaml
frontend:
  ports:
    - "3001:3000"  # Внешний порт 3001

backend:
  ports:
    - "5001:5000"  # Внешний порт 5001
```

Не забудьте обновить `VITE_BACKEND_URL` в `.env`.

### Бэкенд не запускается

Проверьте логи:
```bash
docker compose logs backend
```

Частые проблемы:
- Нет ffmpeg → уже установлен в образе
- Нет зависимостей → `docker compose up --build` пересоберёт

### Фронтенд не видит бэкенд

1. Проверьте что бэкенд запущен:
   ```bash
   curl http://localhost:5000/health
   ```

2. Проверьте `VITE_BACKEND_URL` в `.env`

3. Перезапустите фронт:
   ```bash
   docker compose restart frontend
   ```

### Изменения не применяются

Если hot-reload не работает:
```bash
docker compose down
docker compose up --build
```

### Ошибка "relation does not exist"

Если при сохранении настроек возникает ошибка о несуществующей таблице:

```bash
# Перезапустить бэкенд для выполнения скрипта инициализации
docker compose restart backend

# Проверить логи
docker compose logs backend | grep "Инициализация"
```

Скрипт инициализации автоматически создаёт все таблицы при старте контейнера. Убедитесь, что PostgreSQL доступен перед запуском бэкенда.

**Важно:** После `git pull` обязательно выполняйте `docker compose up --build` (с флагом `--build`), чтобы изменения кода применились в контейнере. Без этого Docker использует закэшированный образ со старой версией кода.

### Приватный ключ не виден при вставке

При вставке приватного ключа в PEM-формате (содержит `-----BEGIN PRIVATE KEY-----`):
- Поле ввода автоматически размывается для безопасности
- Нажмите кнопку **"Показать"** справа от поля, чтобы увидеть содержимое
- Валидация теперь поддерживает оба формата: JSON и PEM

### Ошибка "Неверный формат ключа"

Убедитесь, что ключ в одном из поддерживаемых форматов:
1. **JSON-формат:** полный файл ключа сервисного аккаунта (начинается с `{`)
2. **PEM-формат:** приватный ключ между `-----BEGIN PRIVATE KEY-----` и `-----END PRIVATE KEY-----`

## API бэкенда

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
  -F "language=ru-RU" \
  -F 'nomenclature=["артикул","серийный номер"]'
```

### POST /analyze
Анализ аудиофайла.

```bash
curl -X POST http://localhost:5000/analyze \
  -F "file=@audio.mp3"
```

## Лицензия

MIT
