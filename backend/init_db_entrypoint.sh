#!/bin/bash
set -e

echo "🔄 Инициализация базы данных..."

# Ждем доступности PostgreSQL через Python (psql/pg_isready отсутствуют в slim-образе)
until python -c "
import sqlalchemy, os, sys
url = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/audio_analyzer')
try:
    e = sqlalchemy.create_engine(url, connect_args={'connect_timeout': 3})
    with e.connect() as conn:
        conn.execute(sqlalchemy.text('SELECT 1'))
    sys.exit(0)
except Exception:
    sys.exit(1)
"; do
    echo "⏳ Ожидание PostgreSQL..."
    sleep 2
done

echo "✅ PostgreSQL доступен"

# Создаем таблицы и выполняем легкую автомиграцию схемы через SQLAlchemy
python -c "
from models_db import init_db
print('📦 Создание таблиц и проверка схемы базы данных...')
init_db()
print('✅ Схема БД готова')
" || echo "⚠️  Не удалось инициализировать схему при старте, server.py повторит попытку"

echo "✅ Инициализация завершена"
exec "$@"
