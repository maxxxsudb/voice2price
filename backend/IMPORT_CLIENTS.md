# Импортер клиентов из XLSX

## Описание

Импортер читает XLSX файл с клиентами, валидирует данные и сохраняет результаты в JSON.

## Структура файла

Ожидается файл со следующей структурой:

| Колонка | Название | Тип | Описание |
|---------|----------|-----|----------|
| A | Наименование | string | **Обязательно**. Название клиента |
| B | Код | string | Код клиента |
| C | Бизнес-регион | string | Регион клиента |
| D | Дата регистрации | string | Дата регистрации в системе |
| E | Клиент | string | Тип клиента |
| F | Комментарий | string | Дополнительная информация |
| G | Поставщик | string | Название поставщика |
| H | Публичное наименование | string | Публичное название |
| I | Основной менеджер | string | Ответственный менеджер |
| J | Прочие отношения | string | Другие отношения с клиентом |
| K | Обслуживается торговыми представителями | string | Да/Нет |
| L | Прочая информация | string | (может быть пустой) |
| M | Перевозчик | string | Название перевозчика |
| N | Шаблон этикетки | string | (может быть пустым) |
| O | Юр/Физлицо | string | Юр или Физ |
| P | Пол | string | (может быть пустым) |
| Q | Дата рождения | string | (может быть пустой) |
| R | Вариант отправки электронного чека | string | (может быть пустым) |
| S | Зона доставки | string | (может быть пустой) |
| T | Вид цен | string | (может быть пустым) |
| U | Индивидуальный вид цены | string | (может быть пустым) |
| V | Водитель | string | Ответственный водитель |
| W | Ак флаг спец цена | string | Флаг специальной цены |

## Использование

### 1. Запуск импортера

```bash
cd backend
python import_clients.py Клиенты.xlsx
```

### 2. Результат

Импортер создаст файл `Клиенты.import.json` со структурой:

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

### 3. Валидация

Импортер проверяет:
- ✅ Наименование не пустое
- ✅ Юр/Физлицо имеет допустимое значение (Юр, Физ, Юр., Физ., Юридическое, Физическое)

Ошибки валидации сохраняются в поле `error_message` для каждой строки.

## Пример вывода

```
======================================================================
👥 ИМПОРТ КЛИЕНТОВ
======================================================================
📁 Файл: Клиенты.xlsx
📖 Загружаем workbook...
📄 Лист: Лист_1
📋 Найдено колонок: 23
   1. Наименование
   2. Код
   3. Бизнес-регион
   ...

🔄 Импортируем данные...
✅ Прочитано строк: 131

🔍 Валидация данных...
✅ Валидных: 128
❌ Ошибок: 3
   ❌ Строка 45: Наименование обязательно
   ❌ Строка 123: Недопустимый тип Юр/Физлицо: ИП
   ❌ Строка 234: Наименование обязательно

💾 Результаты сохранены: Клиенты.import.json

📊 Статистика по полям:
   Наименование: 128 заполнено
   Код: 128 заполнено
   Бизнес-регион: 125 заполнено
   Дата регистрации: 128 заполнено
   Основной менеджер: 118 заполнено
   Перевозчик: 128 заполнено
   Водитель: 56 заполнено
   Юр/Физлицо: 128 заполнено

======================================================================
✅ ИМПОРТ ЗАВЕРШЁН
======================================================================

👥 Импортировано: 128 из 131 клиентов
⚠️  Ошибок валидации: 3
   Подробности в файле: Клиенты.import.json
```

## Обработка ошибок

### Ошибка: Файл не найден
```bash
❌ Ошибка: Файл не найден: nonexistent.xlsx
```
**Решение:** Проверьте путь к файлу

### Ошибка: Неправильное расширение
```bash
❌ Ошибка: Файл должен быть .xlsx, получено: .xls
```
**Решение:** Конвертируйте файл в формат .xlsx

### Ошибка: Модуль не установлен
```bash
❌ Установите openpyxl:
   pip install openpyxl
```
**Решение:** Установите зависимости
```bash
pip install -r requirements.txt
```

## Следующие шаги

После импорта:

1. **Проверьте результаты** в файле `.import.json`
2. **Исправьте ошибки** в исходном XLSX файле
3. **Запустите импортер снова** для повторной валидации
4. **Загрузите данные** в базу данных (следующий этап)

## Интеграция с базой данных

Для загрузки в базу данных добавьте функцию:

```python
def save_to_database(clients: List[Client]):
    """Сохранить в базу данных"""
    # Пример с SQLite
    import sqlite3
    
    conn = sqlite3.connect('clients.db')
    cursor = conn.cursor()
    
    # Создание таблицы
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT,
            business_region TEXT,
            registration_date TEXT,
            client TEXT,
            comment TEXT,
            supplier TEXT,
            public_name TEXT,
            main_manager TEXT,
            other_relations TEXT,
            serviced_by_sales_reps TEXT,
            other_info TEXT,
            carrier TEXT,
            label_template TEXT,
            legal_entity_type TEXT,
            gender TEXT,
            birth_date TEXT,
            receipt_delivery_method TEXT,
            delivery_zone TEXT,
            price_type TEXT,
            individual_price_type TEXT,
            driver TEXT,
            special_price_flag TEXT,
            row_number INTEGER,
            import_status TEXT,
            error_message TEXT
        )
    ''')
    
    # Вставка данных
    for client in clients:
        if client.import_status == 'success':
            cursor.execute('''
                INSERT INTO clients 
                (name, code, business_region, registration_date, client,
                 comment, supplier, public_name, main_manager, other_relations,
                 serviced_by_sales_reps, other_info, carrier, label_template,
                 legal_entity_type, gender, birth_date, receipt_delivery_method,
                 delivery_zone, price_type, individual_price_type, driver,
                 special_price_flag, row_number, import_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                client.name, client.code, client.business_region,
                client.registration_date, client.client, client.comment,
                client.supplier, client.public_name, client.main_manager,
                client.other_relations, client.serviced_by_sales_reps,
                client.other_info, client.carrier, client.label_template,
                client.legal_entity_type, client.gender, client.birth_date,
                client.receipt_delivery_method, client.delivery_zone,
                client.price_type, client.individual_price_type,
                client.driver, client.special_price_flag,
                client.row_number, client.import_status
            ))
    
    conn.commit()
    conn.close()
```

## Зависимости

```bash
pip install openpyxl
```

Или установите все зависимости:
```bash
pip install -r requirements.txt
```

## Файлы

- `import_clients.py` - скрипт импортера
- `Клиенты.xlsx` - исходный файл
- `Клиенты.import.json` - результаты импорта

## Поддержка

Если возникли проблемы:
1. Проверьте логи в консоли
2. Проверьте структуру XLSX файла
3. Убедитесь что все зависимости установлены
4. Пришлите ошибку и структуру файла
