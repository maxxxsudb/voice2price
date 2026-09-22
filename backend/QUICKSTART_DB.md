# PostgreSQL + Redis: Быстрый старт

## Что добавлено

✅ **PostgreSQL 16** - основная база данных  
✅ **Redis 7** - кэш для словарей  
✅ **SQLAlchemy** - ORM для работы с БД  
✅ **pgAdmin** (опционально) - веб-интерфейс для управления БД  

## Запуск

### 1. Запустить все сервисы

```bash
docker compose up -d
```

Это запустит:
- Frontend (порт 3000)
- Backend (порт 5000)
- PostgreSQL (порт 5432)
- Redis (порт 6379)

### 2. Проверить статус

```bash
docker compose ps
```

Должно быть:
```
audio-analyzer-frontend    Up
audio-analyzer-backend     Up
audio-analyzer-postgres    Up (healthy)
audio-analyzer-redis       Up (healthy)
```

### 3. Проверить подключения

```bash
# Войти в контейнер бэкенда
docker compose exec backend bash

# Проверить БД и Redis
python database.py
```

## Использование

### Импорт данных

```bash
# Войти в контейнер
docker compose exec backend bash

# Импортировать номенклатуру
python import_nomenclature_db.py ivanov nomenclature.xlsx

# Импортировать клиентов
python import_clients_db.py ivanov clients.xlsx
```

### Управление словарем

```bash
# Просмотр словаря
python manage_voice_dict_db.py ivanov list

# Добавить вариант
python manage_voice_dict_db.py ivanov add "Молоко Домик" "молоко домик" nomenclature

# Экспорт в формате SpeechKit
python manage_voice_dict_db.py ivanov speechkit
```

## Подключение к БД

### Через psql

```bash
docker compose exec postgres psql -U postgres -d audio_analyzer
```

### Через pgAdmin

1. Запустить pgAdmin:
```bash
docker compose --profile tools up -d
```

2. Открыть http://localhost:8080
3. Войти: admin@example.com / admin
4. Добавить сервер:
   - Host: postgres
   - Port: 5432
   - Username: postgres
   - Password: postgres

## Подключение к Redis

```bash
docker compose exec redis redis-cli
```

Полезные команды:
```bash
KEYS *                    # Все ключи
GET dictionary:ivanov     # Словарь сотрудника
DEL dictionary:ivanov     # Удалить кэш
FLUSHDB                   # Очистить весь кэш
```

## Структура БД

### Таблицы

1. **employees** - Сотрудники
2. **nomenclature** - Номенклатура
3. **clients** - Клиенты
4. **voice_dictionary** - Словарь для распознавания
5. **voice_variants** - Варианты произношения
6. **orders** - Заказы
7. **order_items** - Позиции заказа

### Индексы

- employee_id для всех таблиц
- name для nomenclature и clients
- original и variant для словарей
- created_at для orders

## Переменные окружения

```env
# PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/audio_analyzer

# Redis
REDIS_URL=redis://redis:6379/0
```

## Бэкап

### PostgreSQL

```bash
# Создать бэкап
docker compose exec postgres pg_dump -U postgres audio_analyzer > backup.sql

# Восстановить
cat backup.sql | docker compose exec -T postgres psql -U postgres audio_analyzer
```

### Redis

```bash
# Создать снимок
docker compose exec redis redis-cli BGSAVE

# Скопировать файл
docker compose cp redis:/data/dump.rdb ./redis_backup.rdb
```

## Решение проблем

### PostgreSQL не запускается

```bash
docker compose logs postgres
docker compose restart postgres
```

### Redis не запускается

```bash
docker compose logs redis
docker compose restart redis
```

### Ошибка подключения

```bash
# Проверить переменные окружения
docker compose exec backend env | grep DATABASE
docker compose exec backend env | grep REDIS

# Проверить подключение
docker compose exec backend python database.py
```

## Документация

- [DATABASE_SETUP.md](DATABASE_SETUP.md) - полное руководство
- [models_db.py](models_db.py) - SQLAlchemy модели
- [repositories.py](repositories.py) - репозитории для работы с БД
- [database.py](database.py) - подключение к БД и Redis

## Следующие шаги

1. ✅ Настроить PostgreSQL + Redis
2. ✅ Создать модели SQLAlchemy
3. ✅ Создать репозитории
4. ✅ Обновить импортеры для работы с БД
5. ⏳ Обновить API endpoints
6. ⏳ Добавить миграции (Alembic)
7. ⏳ Настроить мониторинг
