# Быстрый старт: Система импорта с сотрудниками

## Что нового

✅ **Привязка к сотрудникам** - номенклатура и клиенты привязаны к конкретному сотруднику  
✅ **Голосовые варианты** - можно добавлять сокращения и альтернативные названия  
✅ **Словарь для распознавания** - автоматическое создание словаря для каждого сотрудника  
✅ **Поиск совпадений** - при распознавании речи автоматически находятся совпадения с номенклатурой  

## Как использовать

### 1. Импорт данных для сотрудника

```bash
cd backend

# Импортируем номенклатуру для сотрудника "ivanov"
python import_nomenclature_v2.py ivanov ЦыганковНоменклатура.xlsx

# Импортируем клиентов для сотрудника "ivanov"
python import_clients_v2.py ivanov Клиенты.xlsx
```

### 2. Добавление голосовых вариантов

```bash
# Смотрим список номенклатуры
python manage_voice_variants.py ivanov list

# Добавляем голосовые варианты
python manage_voice_variants.py ivanov add n1a2b3c4 "молоко домик"
python manage_voice_variants.py ivanov add n1a2b3c4 "домик в деревне" 0.9
python manage_voice_variants.py ivanov add n1a2b3c4 "эм дэ ноль один" 0.85
```

### 3. Распознавание речи с использованием словаря

```bash
# Через API
curl -X POST http://localhost:5000/recognize \
  -F "file=@audio.mp3" \
  -F "api_key=YOUR_API_KEY" \
  -F "employee_id=ivanov"
```

Результат будет содержать найденные совпадения с номенклатурой:

```json
{
  "text": "закажи молоко домик три упаковки",
  "nomenclature_matches": [
    {
      "item_id": "n1a2b3c4",
      "item_name": "Молоко Домик в деревне 3.2%",
      "matched_as": "молоко домик",
      "article": "MD-001"
    }
  ]
}
```

## Структура данных

```
Сотрудник (ivanov.json)
├── Номенклатура (315 записей)
│   ├── Название: "Молоко Домик в деревне 3.2%"
│   ├── Артикул: "MD-001"
│   ├── Код: "12345"
│   └── Голосовые варианты:
│       ├── "молоко домик" (уверенность: 1.0)
│       ├── "домик в деревне" (уверенность: 0.9)
│       └── "эм дэ ноль один" (уверенность: 0.85)
└── Клиенты (128 записей)
    ├── Название: "ООО Ромашка"
    ├── Код: "CL-001"
    └── Регион: "Москва"
```

## API Endpoints

```bash
# Список сотрудников
GET /employees

# Информация о сотруднике
GET /employees/ivanov

# Номенклатура сотрудника
GET /employees/ivanov/nomenclature

# Словарь для распознавания
GET /employees/ivanov/dictionary

# Распознавание с использованием словаря
POST /recognize
  - file: аудиофайл
  - api_key: ключ SpeechKit
  - employee_id: ID сотрудника (опционально)
```

## Команды

### Импорт
```bash
python import_nomenclature_v2.py <employee_id> <file.xlsx>
python import_clients_v2.py <employee_id> <file.xlsx>
```

### Управление голосовыми вариантами
```bash
python manage_voice_variants.py <employee_id> list
python manage_voice_variants.py <employee_id> add <item_id> <variant> [confidence]
python manage_voice_variants.py <employee_id> export
python manage_voice_variants.py <employee_id> speechkit
```

## Примеры

### Пример 1: Полный цикл

```bash
# 1. Импорт данных
python import_nomenclature_v2.py ivanov nomenclature.xlsx
python import_clients_v2.py ivanov clients.xlsx

# 2. Добавление голосовых вариантов
python manage_voice_variants.py ivanov list
python manage_voice_variants.py ivanov add n1a2b3c4 "молоко домик"
python manage_voice_variants.py ivanov add n1a2b3c4 "домик" 0.8

# 3. Экспорт словаря
python manage_voice_variants.py ivanov export

# 4. Распознавание с использованием словаря
curl -X POST http://localhost:5000/recognize \
  -F "file=@audio.mp3" \
  -F "api_key=YOUR_KEY" \
  -F "employee_id=ivanov"
```

### Пример 2: Множество сотрудников

```bash
# Импорт для разных сотрудников
python import_nomenclature_v2.py ivanov ivanov_nomenclature.xlsx
python import_nomenclature_v2.py petrov petrov_nomenclature.xlsx
python import_nomenclature_v2.py sidorov sidorov_nomenclature.xlsx

# Каждый сотрудник имеет свой словарь
curl http://localhost:5000/employees/ivanov/dictionary
curl http://localhost:5000/employees/petrov/dictionary
curl http://localhost:5000/employees/sidorov/dictionary
```

## Файлы данных

Все данные сохраняются в папке `backend/data/`:

```
data/
├── ivanov.json      # Данные сотрудника ivanov
├── petrov.json      # Данные сотрудника petrov
└── sidorov.json     # Данные сотрудника sidorov
```

Каждый файл содержит:
- Информацию о сотруднике
- Номенклатуру с голосовыми вариантами
- Клиентов

## Преимущества

1. **Персонализация** - каждый сотрудник имеет свой словарь
2. **Точность** - голосовые варианты улучшают распознавание
3. **Гибкость** - можно добавлять сокращения и альтернативные названия
4. **Автоматизация** - автоматический поиск совпадений при распознавании
5. **Масштабируемость** - легко добавлять новых сотрудников

## Документация

- [EMPLOYEE_IMPORT_GUIDE.md](EMPLOYEE_IMPORT_GUIDE.md) - полное руководство
- [models.py](models.py) - модели данных
- [manage_voice_variants.py](manage_voice_variants.py) - управление голосовыми вариантами

## Следующие шаги

1. ✅ Импортировать данные для сотрудников
2. ✅ Добавить голосовые варианты
3. ⏳ Протестировать распознавание с использованием словаря
4. ⏳ Настроить интеграцию с Яндекс SpeechKit
5. ⏳ Создать веб-интерфейс для управления
