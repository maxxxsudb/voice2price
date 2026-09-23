"""
SQLAlchemy модели для базы данных.
"""

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import engine
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Employee(Base):
    """Сотрудник"""
    __tablename__ = 'employees'
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    position = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    nomenclature = relationship("Nomenclature", back_populates="employee", cascade="all, delete-orphan")
    clients = relationship("Client", back_populates="employee", cascade="all, delete-orphan")
    voice_dictionary = relationship("VoiceDictionary", back_populates="employee", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="employee", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'position': self.position,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Nomenclature(Base):
    """Номенклатура"""
    __tablename__ = 'nomenclature'
    
    id = Column(String(255), primary_key=True)
    employee_id = Column(String(255), ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(500), nullable=False)
    article = Column(String(255))
    code = Column(String(255))
    weight_unit = Column(String(50))
    weight_denominator = Column(Float)
    weight = Column(String(255))
    weight_numerator = Column(Float)
    nomenclature_type = Column(String(255))
    report_unit = Column(String(255))
    storage_unit = Column(String(255))
    gtin = Column(String(255))
    row_number = Column(Integer)
    import_status = Column(String(50), default='pending')
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    employee = relationship("Employee", back_populates="nomenclature")
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'name': self.name,
            'article': self.article,
            'code': self.code,
            'weight_unit': self.weight_unit,
            'weight_denominator': self.weight_denominator,
            'weight': self.weight,
            'weight_numerator': self.weight_numerator,
            'nomenclature_type': self.nomenclature_type,
            'report_unit': self.report_unit,
            'storage_unit': self.storage_unit,
            'gtin': self.gtin,
            'row_number': self.row_number,
            'import_status': self.import_status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Client(Base):
    """Клиент"""
    __tablename__ = 'clients'
    
    id = Column(String(255), primary_key=True)
    employee_id = Column(String(255), ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(500), nullable=False)
    code = Column(String(255))
    business_region = Column(String(255))
    main_manager = Column(String(255))
    registration_date = Column(String(100))
    client_type = Column(String(255))
    comment = Column(Text)
    supplier = Column(String(500))
    public_name = Column(String(500))
    other_relations = Column(Text)
    serviced_by_sales_reps = Column(String(255))
    carrier = Column(String(500))
    legal_entity_type = Column(String(255))
    driver = Column(String(255))
    special_price_flag = Column(String(255))
    row_number = Column(Integer)
    import_status = Column(String(50), default='pending')
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    employee = relationship("Employee", back_populates="clients")
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'name': self.name,
            'code': self.code,
            'business_region': self.business_region,
            'main_manager': self.main_manager,
            'registration_date': self.registration_date,
            'client_type': self.client_type,
            'comment': self.comment,
            'supplier': self.supplier,
            'public_name': self.public_name,
            'other_relations': self.other_relations,
            'serviced_by_sales_reps': self.serviced_by_sales_reps,
            'carrier': self.carrier,
            'legal_entity_type': self.legal_entity_type,
            'driver': self.driver,
            'special_price_flag': self.special_price_flag,
            'row_number': self.row_number,
            'import_status': self.import_status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class VoiceDictionary(Base):
    """Запись в словаре для распознавания"""
    __tablename__ = 'voice_dictionary'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(255), ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    original = Column(String(500), nullable=False)
    category = Column(String(50), nullable=False)  # client, nomenclature
    item_id = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    employee = relationship("Employee", back_populates="voice_dictionary")
    variants = relationship("VoiceVariant", back_populates="dictionary", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'original': self.original,
            'category': self.category,
            'item_id': self.item_id,
            'variants': [v.to_dict() for v in self.variants],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class VoiceVariant(Base):
    """Вариант произношения"""
    __tablename__ = 'voice_variants'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dictionary_id = Column(Integer, ForeignKey('voice_dictionary.id', ondelete='CASCADE'), nullable=False)
    variant = Column(String(500), nullable=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    dictionary = relationship("VoiceDictionary", back_populates="variants")
    
    def to_dict(self):
        return {
            'id': self.id,
            'variant': self.variant,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Order(Base):
    """Заказ"""
    __tablename__ = 'orders'
    
    id = Column(String(255), primary_key=True)
    employee_id = Column(String(255), ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    client_id = Column(String(255), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    client_name = Column(String(500), nullable=False)
    raw_text = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    employee = relationship("Employee", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'client_id': self.client_id,
            'client_name': self.client_name,
            'raw_text': self.raw_text,
            'items': [item.to_dict() for item in self.items],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class OrderItem(Base):
    """Позиция заказа"""
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(255), ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    nomenclature_id = Column(String(255), ForeignKey('nomenclature.id', ondelete='CASCADE'), nullable=False)
    nomenclature_name = Column(String(500), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="items")
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'nomenclature_id': self.nomenclature_id,
            'nomenclature_name': self.nomenclature_name,
            'quantity': self.quantity,
            'unit': self.unit,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class UnitOfMeasure(Base):
    """Единица измерения"""
    __tablename__ = 'units_of_measure'
    
    id = Column(String(255), primary_key=True)
    employee_id = Column(String(255), ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)  # Название (кг, шт, упаковка)
    abbreviation = Column(String(50))  # Аббревиатура (кг, шт, уп)
    category = Column(String(100))  # Категория (вес, количество, объем)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    employee = relationship("Employee", backref="units")
    variants = relationship("UnitVariant", back_populates="unit", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'name': self.name,
            'abbreviation': self.abbreviation,
            'category': self.category,
            'variants': [v.to_dict() for v in self.variants],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class UnitVariant(Base):
    """Вариант произношения единицы измерения"""
    __tablename__ = 'unit_variants'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    unit_id = Column(String(255), ForeignKey('units_of_measure.id', ondelete='CASCADE'), nullable=False)
    variant = Column(String(255), nullable=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    unit = relationship("UnitOfMeasure", back_populates="variants")
    
    def to_dict(self):
        return {
            'id': self.id,
            'variant': self.variant,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


DEFAULT_ORDER_PROMPT = """Ты — ассистент по обработке заказов медицинской номенклатуры.
Из текста заказа извлеки каждую позицию и верни ТОЛЬКО валидный JSON
массив объектов со строгими полями:
- "name": название товара (нормализованное, как в номенклатуре)
- "quantity": количество (число)
- "unit": единица измерения (шт, уп, упак, мл и т.п.)
Если количество не указано — ставь 1.
Никакого текста вне JSON, только массив."""


class YandexCloudSettings(Base):
    """Настройки Яндекс Облака (рабочая схема: SpeechKit v2 + Object Storage + YandexGPT).

    Используются параметры: api_key, folder_id, bucket_name,
    access_key_id, secret_access_key, order_prompt, yandex_model.
    Один и тот же API-ключ SpeechKit подходит и для YandexGPT (ai.api.cloud.yandex.net).
    Прочие исторические колонки (service_account_key / service_account_id /
    endpoint / iam_token) в схеме не участвуют и из кода удалены.
    """
    __tablename__ = 'yandex_cloud_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key = Column(Text, nullable=True)  # API-ключ сервисного аккаунта SpeechKit/YandexGPT (AQVN...)
    folder_id = Column(String(255), nullable=True)  # Folder ID для SpeechKit (b1g...)
    bucket_name = Column(String(255), nullable=True)  # Имя бакета Object Storage
    access_key_id = Column(String(255), nullable=True)  # S3 Access Key (YCAJE...)
    secret_access_key = Column(Text, nullable=True)  # S3 Secret Key (YCONF...)
    # Промт для разбора расшифровки в список заказа через YandexGPT
    order_prompt = Column(Text, nullable=True)
    # Модель YandexGPT: yandexgpt-lite / yandexgpt / yandexgpt-pro
    yandex_model = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'folder_id': self.folder_id,
            'bucket_name': self.bucket_name,
            'access_key_id': self.access_key_id,
            # Промт и модель — не секреты, возвращаем целиком (для отображения в UI)
            'order_prompt': self.order_prompt or DEFAULT_ORDER_PROMPT,
            'yandex_model': self.yandex_model or 'yandexgpt',
            # Чувствительные данные не возвращаем — только факт заполнения
            'has_api_key': self.api_key is not None,
            'has_secret_access_key': self.secret_access_key is not None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# Создание таблиц
def init_db():
    """Создать все таблицы + автоматически добавить недостающие колонки (легкая миграция)."""
    from sqlalchemy import inspect, text
    Base.metadata.create_all(bind=engine)

    # create_all НЕ добавляет новые колонки в существующие таблицы.
    # Это было причиной ошибок вида:
    #   column yandex_cloud_settings.service_account_id does not exist
    # и падающего с 500 сохранения настроек. Правим через ALTER TABLE ADD COLUMN IF NOT EXISTS.
    try:
        inspector = inspect(engine)
        added = []
        for table in Base.metadata.sorted_tables:
            tname = table.name
            if not inspector.has_table(tname):
                continue
            existing = {c['name'] for c in inspector.get_columns(tname)}
            for col in table.columns:
                if col.name in existing:
                    continue
                col_type = col.type.compile(dialect=engine.dialect)
                nullable = "NULL" if col.nullable else "NOT NULL DEFAULT NULL"
                with engine.begin() as conn:
                    conn.execute(text(
                        f'ALTER TABLE "{tname}" ADD COLUMN IF NOT EXISTS "{col.name}" {col_type} {nullable}'
                    ))
                added.append(f"{tname}.{col.name}")
        if added:
            print(f"🛠  [MIGRATE] Добавлены недостающие колонки: {', '.join(added)}")
        else:
            print("🛠  [MIGRATE] Схема БД актуальна, новых колонок не требуется")
    except Exception as e:
        print(f"⚠️  [MIGRATE] Автомиграция колонок не выполнена: {e}")


if __name__ == '__main__':
    print("Создание таблиц...")
    init_db()
    print("✅ Таблицы созданы")
