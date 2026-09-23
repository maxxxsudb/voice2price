-- Инициализация базы данных audio_analyzer

-- Таблица сотрудников
CREATE TABLE IF NOT EXISTS employees (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    position VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица номенклатуры
CREATE TABLE IF NOT EXISTS nomenclature (
    id VARCHAR(255) PRIMARY KEY,
    employee_id VARCHAR(255) NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    article VARCHAR(255),
    code VARCHAR(255),
    weight_unit VARCHAR(50),
    weight_denominator DECIMAL(10,2),
    weight VARCHAR(255),
    weight_numerator DECIMAL(10,2),
    nomenclature_type VARCHAR(255),
    report_unit VARCHAR(255),
    storage_unit VARCHAR(255),
    gtin VARCHAR(255),
    row_number INTEGER,
    import_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для номенклатуры
CREATE INDEX IF NOT EXISTS idx_nomenclature_employee_id ON nomenclature(employee_id);
CREATE INDEX IF NOT EXISTS idx_nomenclature_name ON nomenclature(name);
CREATE INDEX IF NOT EXISTS idx_nomenclature_article ON nomenclature(article);

-- Таблица клиентов
CREATE TABLE IF NOT EXISTS clients (
    id VARCHAR(255) PRIMARY KEY,
    employee_id VARCHAR(255) NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    code VARCHAR(255),
    business_region VARCHAR(255),
    main_manager VARCHAR(255),
    registration_date VARCHAR(100),
    client_type VARCHAR(255),
    comment TEXT,
    supplier VARCHAR(500),
    public_name VARCHAR(500),
    other_relations TEXT,
    serviced_by_sales_reps VARCHAR(255),
    carrier VARCHAR(500),
    legal_entity_type VARCHAR(255),
    driver VARCHAR(255),
    special_price_flag VARCHAR(255),
    row_number INTEGER,
    import_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для клиентов
CREATE INDEX IF NOT EXISTS idx_clients_employee_id ON clients(employee_id);
CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);
CREATE INDEX IF NOT EXISTS idx_clients_code ON clients(code);

-- Таблица словаря для распознавания
CREATE TABLE IF NOT EXISTS voice_dictionary (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(255) NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    original VARCHAR(500) NOT NULL,
    category VARCHAR(50) NOT NULL,
    item_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для словаря
CREATE INDEX IF NOT EXISTS idx_voice_dictionary_employee_id ON voice_dictionary(employee_id);
CREATE INDEX IF NOT EXISTS idx_voice_dictionary_original ON voice_dictionary(original);
CREATE INDEX IF NOT EXISTS idx_voice_dictionary_category ON voice_dictionary(category);

-- Таблица вариантов произношения
CREATE TABLE IF NOT EXISTS voice_variants (
    id SERIAL PRIMARY KEY,
    dictionary_id INTEGER NOT NULL REFERENCES voice_dictionary(id) ON DELETE CASCADE,
    variant VARCHAR(500) NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для вариантов
CREATE INDEX IF NOT EXISTS idx_voice_variants_dictionary_id ON voice_variants(dictionary_id);
CREATE INDEX IF NOT EXISTS idx_voice_variants_variant ON voice_variants(variant);

-- Таблица заказов
CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR(255) PRIMARY KEY,
    employee_id VARCHAR(255) NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    client_id VARCHAR(255) NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    client_name VARCHAR(500) NOT NULL,
    raw_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для заказов
CREATE INDEX IF NOT EXISTS idx_orders_employee_id ON orders(employee_id);
CREATE INDEX IF NOT EXISTS idx_orders_client_id ON orders(client_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

-- Таблица позиций заказа
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(255) NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    nomenclature_id VARCHAR(255) NOT NULL REFERENCES nomenclature(id) ON DELETE CASCADE,
    nomenclature_name VARCHAR(500) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для позиций заказа
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_nomenclature_id ON order_items(nomenclature_id);

-- Таблица единиц измерения
CREATE TABLE IF NOT EXISTS units_of_measure (
    id VARCHAR(255) PRIMARY KEY,
    employee_id VARCHAR(255) NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    abbreviation VARCHAR(50),
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для единиц измерения
CREATE INDEX IF NOT EXISTS idx_units_employee_id ON units_of_measure(employee_id);
CREATE INDEX IF NOT EXISTS idx_units_name ON units_of_measure(name);

-- Таблица вариантов произношения единиц измерения
CREATE TABLE IF NOT EXISTS unit_variants (
    id SERIAL PRIMARY KEY,
    unit_id VARCHAR(255) NOT NULL REFERENCES units_of_measure(id) ON DELETE CASCADE,
    variant VARCHAR(255) NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для вариантов единиц измерения
CREATE INDEX IF NOT EXISTS idx_unit_variants_unit_id ON unit_variants(unit_id);
CREATE INDEX IF NOT EXISTS idx_unit_variants_variant ON unit_variants(variant);

-- Функция для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для employees
CREATE TRIGGER update_employees_updated_at BEFORE UPDATE ON employees
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Представление для быстрого доступа к словарю сотрудника
CREATE OR REPLACE VIEW employee_dictionary_view AS
SELECT 
    e.id as employee_id,
    e.name as employee_name,
    vd.original,
    vd.category,
    vd.item_id,
    array_agg(vv.variant) as variants
FROM employees e
JOIN voice_dictionary vd ON e.id = vd.employee_id
LEFT JOIN voice_variants vv ON vd.id = vv.dictionary_id
GROUP BY e.id, e.name, vd.original, vd.category, vd.item_id;

-- Представление для статистики сотрудников
CREATE OR REPLACE VIEW employee_stats_view AS
SELECT 
    e.id,
    e.name,
    e.email,
    COUNT(DISTINCT n.id) as nomenclature_count,
    COUNT(DISTINCT c.id) as clients_count,
    COUNT(DISTINCT o.id) as orders_count,
    COUNT(DISTINCT vd.id) as dictionary_entries_count
FROM employees e
LEFT JOIN nomenclature n ON e.id = n.employee_id AND n.import_status = 'success'
LEFT JOIN clients c ON e.id = c.employee_id AND c.import_status = 'success'
LEFT JOIN orders o ON e.id = o.employee_id
LEFT JOIN voice_dictionary vd ON e.id = vd.employee_id
GROUP BY e.id, e.name, e.email;

-- Таблица настроек Яндекс Облака
CREATE TABLE IF NOT EXISTS yandex_cloud_settings (
    id SERIAL PRIMARY KEY,
    service_account_key TEXT,
    service_account_id VARCHAR(255),
    api_key TEXT,
    folder_id VARCHAR(255),
    bucket_name VARCHAR(255),
    endpoint VARCHAR(255) DEFAULT 'https://storage.yandexcloud.net',
    access_key_id VARCHAR(255),
    secret_access_key TEXT,
    iam_token TEXT,
    iam_token_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
