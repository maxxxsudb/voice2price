# Настройка PostgreSQL + Redis

## Архитектура

```
┌─────────────────┐
│   Frontend      │
│   (React)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Backend       │
│   (Flask)       │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│Postgres│ │ Redis  │
│   DB   │ │ Cache  │
└────────┘ └────────┘
```

## Компоненты

### PostgreSQL
- **Порт:** 5432
- **Пользователь:** postgres
- **Пароль:** postgres
- **База данных:** audio_analyzer
- **Данные:** Сотрудники, клиенты, номенклатура, заказы, словари

### Redis
- **Порт:** 6379
- **Использование:** Кэш словарей для быстрого доступа
- **TTL:** 1 час для словарей, 30 минут для данных сотрудников

### pgAdmin (опционально)
- **Порт:** 8080
- **Email:** admin@example.com
- **Пароль:** admin
- **Запуск:** `docker compose --profile tools up`

## Быстрый старт

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

# Проверить БД
python database.py

# Проверить репозитории
python repositories.py
```

## Структура базы данных

### Таблицы

1. **employees** - Сотрудники
   - id, name, email, phone, position
   - created_at, updated_at

2. **nomenclature** - Номенклатура
   - id, employee_id, name, article, code
   - weight_unit, weight_denominator, weight, weight_numerator
   - nomenclature_type, report_unit, storage_unit, gtin
   - row_number, import_status, error_message

3. **clients** - Клиенты
   - id, employee_id, name, code
   - business_region, main_manager, registration_date
   - client_type, comment, supplier, public_name
   - other_relations, serviced_by_sales_reps, carrier
   - legal_entity_type, driver, special_price_flag
   - row_number, import_status, error_message

4. **voice_dictionary** - Словарь для распознавания
   - id, employee_id, original, category, item_id

5. **voice_variants** - Варианты произношения
   - id, dictionary_id, variant, confidence

6. **orders** - Заказы
   - id, employee_id, client_id, client_name, raw_text

7. **order_items** - Позиции заказа
   - id, order_id, nomenclature_id, nomenclature_name, quantity, unit

### Индексы

- employee_id для всех таблиц
- name для nomenclature и clients
- original и variant для voice_dictionary и voice_variants
- created_at для orders

### Представления

- **employee_dictionary_view** - Быстрый доступ к словарю сотрудника
- **employee_stats_view** - Статистика по сотрудникам

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

### API запросы

```bash
# Список сотрудников
curl http://localhost:5000/employees

# Информация о сотруднике
curl http://localhost:5000/employees/ivanov

# Словарь сотрудника
curl http://localhost:5000/employees/ivanov/dictionary

# Распознавание с парсингом
curl -X POST http://localhost:5000/recognize \
  -F "file=@audio.mp3" \
  -F "api_key=YOUR_KEY" \
  -F "employee_id=ivanov"
```

## Подключение к БД

### Из контейнера

```bash
docker compose exec postgres psql -U postgres -d audio_analyzer
```

### Из хоста

```bash
psql -h localhost -p 5432 -U postgres -d audio_analyzer
```

### Через pgAdmin

1. Открыть http://localhost:8080
2. Войти: admin@example.com / admin
3. Добавить сервер:
   - Host: postgres
   - Port: 5432
   - Username: postgres
   - Password: postgres

## Подключение к Redis

### Из контейнера

```bash
docker compose exec redis redis-cli
```

### Из хоста

```bash
redis-cli -h localhost -p 6379
```

### Полезные команды

```bash
# Посмотреть все ключи
KEYS *

# Посмотреть словарь сотрудника
GET dictionary:ivanov

# Удалить кэш
DEL dictionary:ivanov

# Очистить весь кэш
FLUSHDB
```

## Мониторинг

### PostgreSQL

```bash
# Статистика подключений
SELECT count(*) FROM pg_stat_activity;

# Размер базы данных
SELECT pg_size_pretty(pg_database_size('audio_analyzer'));

# Топ таблиц по размеру
SELECT 
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 10;
```

### Redis

```bash
# Информация о Redis
INFO

# Использование памяти
INFO memory

# Статистика команд
INFO stats
```

## Бэкап и восстановление

### Бэкап PostgreSQL

```bash
# Создать бэкап
docker compose exec postgres pg_dump -U postgres audio_analyzer > backup.sql

# Восстановить из бэкапа
cat backup.sql | docker compose exec -T postgres psql -U postgres audio_analyzer
```

### Бэкап Redis

```bash
# Создать снимок
docker compose exec redis redis-cli BGSAVE

# Скопировать файл
docker compose cp redis:/data/dump.rdb ./redis_backup.rdb
```

## Решение проблем

### PostgreSQL не запускается

```bash
# Проверить логи
docker compose logs postgres

# Перезапустить
docker compose restart postgres

# Пересоздать volume (ВНИМАНИЕ: удалит все данные!)
docker compose down -v
docker compose up -d
```

### Redis не запускается

```bash
# Проверить логи
docker compose logs redis

# Перезапустить
docker compose restart redis
```

### Ошибка подключения к БД

```bash
# Проверить что БД запущена
docker compose ps postgres

# Проверить переменные окружения
docker compose exec backend env | grep DATABASE

# Проверить подключение
docker compose exec backend python database.py
```

### Кэш не обновляется

```bash
# Очистить кэш
docker compose exec redis redis-cli FLUSHDB

# Или через API
curl -X POST http://localhost:5000/cache/clear
```

## Производительность

### Оптимизация PostgreSQL

```sql
-- Анализ запросов
EXPLAIN ANALYZE SELECT * FROM nomenclature WHERE employee_id = 'ivanov';

-- Обновить статистику
ANALYZE nomenclature;
ANALYZE clients;
ANALYZE voice_dictionary;

-- Ваккуум
VACUUM ANALYZE;
```

### Оптимизация Redis

```bash
# Настроить maxmemory
CONFIG SET maxmemory 256mb
CONFIG SET maxmemory-policy allkeys-lru

# Сохранить настройки
CONFIG REWRITE
```

## Переменные окружения

```env
# PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/audio_analyzer

# Redis
REDIS_URL=redis://redis:6379/0

# Flask
FLASK_ENV=development
FLASK_DEBUG=1
```

## Следующие шаги

1. ✅ Настроить PostgreSQL + Redis
2. ✅ Создать модели SQLAlchemy
3. ✅ Создать репозитории
4. ⏳ Обновить импортеры для работы с БД
5. ⏳ Обновить API endpoints
6. ⏳ Добавить миграции (Alembic)
7. ⏳ Настроить мониторинг
8. ⏳ Настроить бэкапы
