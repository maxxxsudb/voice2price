# Полное руководство по импорту данных

## Обзор

Система импорта данных из XLSX файлов состоит из:
1. **Анализатора XLSX** - анализирует структуру файла
2. **Импортера номенклатуры** - импортирует товары
3. **Импортера клиентов** - импортирует клиентов
4. **Главного скрипта** - запускает оба импорта

## Структура проекта

```
backend/
├── analyze_xlsx.py          # Анализатор XLSX файлов
├── import_nomenclature.py   # Импортер номенклатуры
├── import_clients.py        # Импортер клиентов
├── import_all.py            # Главный скрипт импорта
├── server.py                # Flask сервер
└── requirements.txt         # Зависимости
```

## Быстрый старт

### 1. Установите зависимости

```bash
cd backend
pip install -r requirements.txt
```

### 2. Проанализируйте файлы

```bash
# Анализ номенклатуры
python analyze_xlsx.py ЦыганковНоменклатура.xlsx

# Анализ клиентов
python analyze_xlsx.py Клиенты.xlsx
```

### 3. Запустите импорт

```bash
# Импорт обоих файлов
python import_all.py ЦыганковНоменклатура.xlsx Клиенты.xlsx
```

Или по отдельности:

```bash
# Только номенклатура
python import_nomenclature.py ЦыганковНоменклатура.xlsx

# Только клиенты
python import_clients.py Клиенты.xlsx
```

## Структура файлов

### Номенклатура (ЦыганковНоменклатура.xlsx)

| Колонка | Название | Тип | Обязательное |
|---------|----------|-----|--------------|
| A | Наименование | string | ✅ Да |
| B | Артикул | string | ❌ Нет |
| C | Единица измерения веса | string | ❌ Нет |
| D | Вес (знаменатель) | number | ❌ Нет |
| E | Вес | string | ❌ Нет |
| F | Вес (числитель) | number | ❌ Нет |
| G | Вид номенклатуры | string | ❌ Нет |
| H | Единица для отчетов | string | ❌ Нет |
| I | Единица хранения | string | ❌ Нет |
| J | GTIN | string | ❌ Нет |
| K | Код | string | ❌ Нет |

**Статистика:** 318 строк × 11 колонок

### Клиенты (Клиенты.xlsx)

| Колонка | Название | Тип | Обязательное |
|---------|----------|-----|--------------|
| A | Наименование | string | ✅ Да |
| B | Код | string | ❌ Нет |
| C | Бизнес-регион | string | ❌ Нет |
| D | Дата регистрации | string | ❌ Нет |
| E | Клиент | string | ❌ Нет |
| F | Комментарий | string | ❌ Нет |
| G | Поставщик | string | ❌ Нет |
| H | Публичное наименование | string | ❌ Нет |
| I | Основной менеджер | string | ❌ Нет |
| J | Прочие отношения | string | ❌ Нет |
| K | Обслуживается торговыми представителями | string | ❌ Нет |
| L | Прочая информация | string | ❌ Нет |
| M | Перевозчик | string | ❌ Нет |
| N | Шаблон этикетки | string | ❌ Нет |
| O | Юр/Физлицо | string | ❌ Нет |
| P | Пол | string | ❌ Нет |
| Q | Дата рождения | string | ❌ Нет |
| R | Вариант отправки электронного чека | string | ❌ Нет |
| S | Зона доставки | string | ❌ Нет |
| T | Вид цен | string | ❌ Нет |
| U | Индивидуальный вид цены | string | ❌ Нет |
| V | Водитель | string | ❌ Нет |
| W | Ак флаг спец цена | string | ❌ Нет |

**Статистика:** 131 строка × 23 колонки

## Результаты импорта

После импорта создаются файлы:

### ЦыганковНоменклатура.import.json

```json
{
  "file": "ЦыганковНоменклатура.xlsx",
  "file_size_mb": 0.03,
  "sheet_name": "Лист_1",
  "total_rows": 318,
  "valid_rows": 315,
  "invalid_rows": 3,
  "items": [
    {
      "name": "Товар 1",
      "article": "ART-001",
      "weight_unit": "кг",
      "weight_denominator": 1.5,
      "weight": "1.5 кг",
      "weight_numerator": 1.5,
      "nomenclature_type": "Продукты",
      "report_unit": "кг",
      "storage_unit": "кг",
      "gtin": null,
      "code": "CODE-001",
      "row_number": 2,
      "import_status": "success",
      "error_message": null
    }
  ],
  "import_time": "2026-09-22T07:15:30.123456"
}
```

### Клиенты.import.json

```json
{
  "file": "Клиенты.xlsx",
  "file_size_mb": 0.02,
  "sheet_name": "Лист_1",
  "total_rows": 131,
  "valid_rows": 128,
  "invalid_rows": 3,
  "clients": [
    {
      "name": "ООО Пример",
      "code": "CL-001",
      "business_region": "Москва",
      "registration_date": "2024-01-15",
      "client": "Постоянный",
      "comment": null,
      "supplier": "Поставщик 1",
      "public_name": "Пример",
      "main_manager": "Иванов И.И.",
      "other_relations": null,
      "serviced_by_sales_reps": "Да",
      "other_info": null,
      "carrier": "Перевозчик 1",
      "label_template": null,
      "legal_entity_type": "Юр",
      "gender": null,
      "birth_date": null,
      "receipt_delivery_method": null,
      "delivery_zone": null,
      "price_type": null,
      "individual_price_type": null,
      "driver": "Петров П.П.",
      "special_price_flag": "Нет",
      "row_number": 2,
      "import_status": "success",
      "error_message": null
    }
  ],
  "import_time": "2026-09-22T07:20:30.123456"
}
```

## Валидация данных

### Номенклатура

Проверяется:
- ✅ Наименование не пустое
- ✅ Вес (знаменатель) > 0 если указан
- ✅ Вес (числитель) > 0 если указан

### Клиенты

Проверяется:
- ✅ Наименование не пустое
- ✅ Юр/Физлицо имеет допустимое значение (Юр, Физ, Юр., Физ., Юридическое, Физическое)

## Обработка ошибок

Если есть ошибки валидации:

1. Откройте файл `.import.json`
2. Найдите записи с `import_status: "error"`
3. Посмотрите `error_message`
4. Исправьте ошибки в исходном XLSX файле
5. Запустите импорт снова

Пример ошибки:
```json
{
  "name": "",
  "row_number": 45,
  "import_status": "error",
  "error_message": "Наименование обязательно"
}
```

## Интеграция с базой данных

### SQLite

Пример функции для загрузки в SQLite:

```python
import sqlite3

def save_to_database(items, table_name):
    """Сохранить в базу данных SQLite"""
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    
    # Создание таблицы (пример для номенклатуры)
    if table_name == 'nomenclature':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nomenclature (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                article TEXT,
                weight_unit TEXT,
                weight_denominator REAL,
                weight TEXT,
                weight_numerator REAL,
                nomenclature_type TEXT,
                report_unit TEXT,
                storage_unit TEXT,
                gtin TEXT,
                code TEXT,
                row_number INTEGER,
                import_status TEXT,
                error_message TEXT
            )
        ''')
    
    # Вставка данных
    for item in items:
        if item['import_status'] == 'success':
            # Вставка записи
            pass
    
    conn.commit()
    conn.close()
```

### PostgreSQL

Пример для PostgreSQL:

```python
import psycopg2

def save_to_postgres(items, table_name):
    """Сохранить в PostgreSQL"""
    conn = psycopg2.connect(
        host="localhost",
        database="mydb",
        user="myuser",
        password="mypassword"
    )
    cursor = conn.cursor()
    
    # Вставка данных
    for item in items:
        if item['import_status'] == 'success':
            cursor.execute('''
                INSERT INTO nomenclature (name, article, ...)
                VALUES (%s, %s, ...)
            ''', (item['name'], item['article'], ...))
    
    conn.commit()
    cursor.close()
    conn.close()
```

## Docker

### Запуск в Docker

```bash
# Запустить контейнер
docker compose up -d backend

# Войти в контейнер
docker compose exec backend bash

# Запустить импорт
python import_all.py /data/ЦыганковНоменклатура.xlsx /data/Клиенты.xlsx
```

### Монтирование файлов

В `docker-compose.yml`:

```yaml
services:
  backend:
    volumes:
      - ./data:/app/data
```

Положите файлы в папку `data/` и запустите:

```bash
docker compose exec backend python import_all.py /app/data/ЦыганковНоменклатура.xlsx /app/data/Клиенты.xlsx
```

## Логи

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

## Поддержка

Если возникли проблемы:

1. Проверьте логи в консоли
2. Проверьте структуру XLSX файла через `analyze_xlsx.py`
3. Убедитесь что все зависимости установлены
4. Проверьте права доступа к файлам
5. Пришлите ошибку и структуру файла

## Следующие шаги

После успешного импорта:

1. ✅ Проверьте файлы `.import.json`
2. ✅ Исправьте ошибки валидации
3. ✅ Загрузите данные в базу данных
4. ✅ Настройте связи между номенклатурой и клиентами
5. ✅ Создайте API для доступа к данным
6. ✅ Добавьте веб-интерфейс для управления данными

## Полезные команды

```bash
# Анализ файла
python analyze_xlsx.py file.xlsx

# Импорт номенклатуры
python import_nomenclature.py nomenclature.xlsx

# Импорт клиентов
python import_clients.py clients.xlsx

# Импорт обоих файлов
python import_all.py nomenclature.xlsx clients.xlsx

# Проверка результатов
cat nomenclature.import.json | jq '.valid_rows'
cat clients.import.json | jq '.valid_rows'
```

## Зависимости

```txt
flask>=3.0.0
flask-cors>=4.0.0
requests>=2.31.0
pydub>=0.25.1
openpyxl>=3.1.0
```

Установка:
```bash
pip install -r requirements.txt
```
