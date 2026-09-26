"""
Подключение к базе данных PostgreSQL и Redis.

Все данные хранятся в PostgreSQL (схема — models_db.py, доступ — repositories.py).
Redis — только кэш словаря произношений: без него всё читается из БД.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool
import redis
import json

# PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/audio_analyzer')
# SQLAlchemy 2.1 по умолчанию берёт для postgresql:// драйвер psycopg 3, а установлен psycopg2
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = 'postgresql+psycopg2://' + DATABASE_URL[len('postgresql://'):]

# Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Создаем engine для PostgreSQL
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False
)

# Создаем сессию
Session = scoped_session(sessionmaker(bind=engine))

# Redis клиент
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


def get_session():
    """Получить сессию БД"""
    return Session()


def close_session():
    """Закрыть сессию БД"""
    Session.remove()


# ==================== REDIS CACHE ====================

class DictionaryCache:
    """Кэш для словарей распознавания"""
    
    CACHE_TTL = 3600  # 1 час
    
    @staticmethod
    def get_key(employee_id: str) -> str:
        return f"dictionary:{employee_id}"
    
    @staticmethod
    def get(employee_id: str) -> dict:
        """Получить словарь из кэша"""
        key = DictionaryCache.get_key(employee_id)
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    
    @staticmethod
    def set(employee_id: str, dictionary: dict):
        """Сохранить словарь в кэш"""
        key = DictionaryCache.get_key(employee_id)
        redis_client.setex(key, DictionaryCache.CACHE_TTL, json.dumps(dictionary, ensure_ascii=False))
    
    @staticmethod
    def invalidate(employee_id: str):
        """Удалить словарь из кэша"""
        key = DictionaryCache.get_key(employee_id)
        redis_client.delete(key)
    
    @staticmethod
    def invalidate_all():
        """Очистить весь кэш словарей"""
        keys = redis_client.keys("dictionary:*")
        if keys:
            redis_client.delete(*keys)


# ==================== HEALTH CHECK ====================

def check_database() -> bool:
    """Проверить подключение к БД"""
    try:
        session = get_session()
        session.execute(text("SELECT 1"))
        close_session()
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def check_redis() -> bool:
    """Проверить подключение к Redis"""
    try:
        redis_client.ping()
        return True
    except Exception as e:
        print(f"❌ Redis error: {e}")
        return False


def check_all() -> dict:
    """Проверить все подключения"""
    return {
        'database': check_database(),
        'redis': check_redis()
    }


if __name__ == '__main__':
    print("Проверка подключений...")
    status = check_all()
    print(f"Database: {'✅ OK' if status['database'] else '❌ Error'}")
    print(f"Redis: {'✅ OK' if status['redis'] else '❌ Error'}")
