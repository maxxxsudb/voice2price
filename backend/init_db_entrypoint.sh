#!/bin/bash
set -e

echo "🔄 Инициализация базы данных..."

# Ждем доступности PostgreSQL
until pg_isready -h postgres -p 5432 -U postgres; do
    echo "⏳ Ожидание PostgreSQL..."
    sleep 2
done

echo "✅ PostgreSQL доступен"

# Создаем таблицы через SQLAlchemy
python -c "
from models_db import Base, engine, YandexCloudSettings
print('📦 Создание таблиц в базе данных...')
Base.metadata.create_all(bind=engine)
print('✅ Таблицы созданы успешно')
"

echo "✅ Инициализация завершена"
exec "$@"
