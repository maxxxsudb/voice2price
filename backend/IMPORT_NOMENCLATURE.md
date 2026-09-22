# Импортер номенклатуры из XLSX

## Описание

Импортер читает XLSX файл с номенклатурой, валидирует данные и сохраняет результаты в JSON.

## Структура файла

Ожидается файл со следующей структурой:

| Колонка | Название | Тип | Описание |
|---------|----------|-----|----------|
| A | Наименование | string | **Обязательно**. Название товара |
| B | Артикул | string | Артикул товара |
| C | Единица измерения веса | string | кг, г, л и т.д. |
| D | Вес (знаменатель) | number | Числовое значение веса |
| E | Вес | string | Текстовое представление веса |
| F | Вес (числитель) | number | Числовое значение веса |
| G | Вид номенклатуры | string | Категория товара |
| H | Единица для отчетов | string | Единица измерения |
| I | Единица хранения | string | Единица хранения |
| J | GTIN | string | Штрих-код (может быть пустым) |
| K | Код | string | Внутренний код |

## Использование

### 1. Запуск импортера

```bash
cd backend
python import_nomenclature.py ЦыганковНоменклатура.xlsx
```

### 2. Результат

Импортер создаст файл `ЦыганковНоменклатура.import.json` со структурой:

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

### 3. Валидация

Импортер проверяет:
- ✅ Наименование не пустое
- ✅ Вес (знаменатель) > 0 если указан
- ✅ Вес (числитель) > 0 если указан

Ошибки валидации сохраняются в поле `error_message` для каждой строки.

## Пример вывода

```
======================================================================
📦 ИМПОРТ НОМЕНКЛАТУРЫ
======================================================================
📁 Файл: ЦыганковНоменклатура.xlsx
📖 Загружаем workbook...
📄 Лист: Лист_1
📋 Найдено колонок: 11
   1. Наименование
   2. Артикул
   3. Единица измерения веса
   ...

🔄 Импортируем данные...
✅ Прочитано строк: 318

🔍 Валидация данных...
✅ Валидных: 315
❌ Ошибок: 3
   ❌ Строка 45: Наименование обязательно
   ❌ Строка 123: Вес (знаменатель) должен быть > 0
   ❌ Строка 234: Наименование обязательно

💾 Результаты сохранены: ЦыганковНоменклатура.import.json

📊 Статистика по полям:
   Наименование: 315 заполнено
   Артикул: 288 заполнено
   Вес (числитель): 198 заполнено
   Вес (знаменатель): 288 заполнено
   Вид номенклатуры: 315 заполнено
   Код: 315 заполнено

======================================================================
✅ ИМПОРТ ЗАВЕРШЁН
======================================================================

📦 Импортировано: 315 из 318 записей
⚠️  Ошибок валидации: 3
   Подробности в файле: ЦыганковНоменклатура.import.json
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
def save_to_database(items: List[NomenclatureItem]):
    """Сохранить в базу данных"""
    # Пример с SQLite
    import sqlite3
    
    conn = sqlite3.connect('nomenclature.db')
    cursor = conn.cursor()
    
    # Создание таблицы
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
        if item.import_status == 'success':
            cursor.execute('''
                INSERT INTO nomenclature 
                (name, article, weight_unit, weight_denominator, weight, 
                 weight_numerator, nomenclature_type, report_unit, 
                 storage_unit, gtin, code, row_number, import_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.name, item.article, item.weight_unit,
                item.weight_denominator, item.weight,
                item.weight_numerator, item.nomenclature_type,
                item.report_unit, item.storage_unit,
                item.gtin, item.code, item.row_number,
                item.import_status
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

- `import_nomenclature.py` - скрипт импортера
- `ЦыганковНоменклатура.xlsx` - исходный файл
- `ЦыганковНоменклатура.import.json` - результаты импорта

## Поддержка

Если возникли проблемы:
1. Проверьте логи в консоли
2. Проверьте структуру XLSX файла
3. Убедитесь что все зависимости установлены
4. Пришлите ошибку и структуру файла
