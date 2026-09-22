# Система импорта с привязкой к сотрудникам

## Обзор

Новая система импорта данных с привязкой к сотрудникам и поддержкой голосовых вариантов номенклатуры для улучшения распознавания речи.

## Структура данных

```
Сотрудник (Employee)
├── ID, имя, email, телефон, должность
├── Номенклатура (Nomenclature[])
│   ├── ID, наименование, артикул, код
│   ├── Вес, единицы измерения
│   ├── Голосовые варианты (VoiceVariant[])
│   └── Привязка к сотруднику
└── Клиенты (Client[])
    ├── ID, наименование, код
    ├── Регион, менеджер, перевозчик
    └── Привязка к сотруднику
```

## Быстрый старт

### 1. Импорт номенклатуры для сотрудника

```bash
cd backend
python import_nomenclature_v2.py ivanov ЦыганковНоменклатура.xlsx
```

### 2. Импорт клиентов для сотрудника

```bash
python import_clients_v2.py ivanov Клиенты.xlsx
```

### 3. Управление голосовыми вариантами

```bash
# Показать список номенклатуры
python manage_voice_variants.py ivanov list

# Добавить голосовой вариант
python manage_voice_variants.py ivanov add n12345678 "молоко домик"

# Добавить с указанием уверенности
python manage_voice_variants.py ivanov add n12345678 "домик в деревне" 0.9

# Экспортировать словарь
python manage_voice_variants.py ivanov export

# Экспортировать в формате SpeechKit
python manage_voice_variants.py ivanov speechkit
```

## Примеры использования

### Сценарий 1: Импорт данных сотрудника

```bash
# 1. Импортируем номенклатуру
python import_nomenclature_v2.py ivanov ЦыганковНоменклатура.xlsx

# Результат:
# ✅ Импортировано: 315 из 318 записей
# 👤 Сотрудник: ivanov
# 📋 Всего номенклатуры у сотрудника: 315

# 2. Импортируем клиентов
python import_clients_v2.py ivanov Клиенты.xlsx

# Результат:
# ✅ Импортировано: 128 из 131 клиентов
# 👤 Сотрудник: ivanov
# 📋 Всего клиентов у сотрудника: 128
```

### Сценарий 2: Добавление голосовых вариантов

```bash
# 1. Смотрим список номенклатуры
python manage_voice_variants.py ivanov list

# Результат:
# 1. [n1a2b3c4] Молоко Домик в деревне 3.2%
#    Артикул: MD-001
#    Код: 12345
#    Голосовые варианты: нет

# 2. Добавляем голосовые варианты
python manage_voice_variants.py ivanov add n1a2b3c4 "молоко домик"
python manage_voice_variants.py ivanov add n1a2b3c4 "домик в деревне" 0.9
python manage_voice_variants.py ivanov add n1a2b3c4 "эм дэ ноль один" 0.85

# 3. Проверяем
python manage_voice_variants.py ivanov list

# Результат:
# 1. [n1a2b3c4] Молоко Домик в деревне 3.2%
#    Артикул: MD-001
#    Код: 12345
#    Голосовые варианты:
#      • молоко домик (уверенность: 1.00)
#      • домик в деревне (уверенность: 0.90)
#      • эм дэ ноль один (уверенность: 0.85)
```

### Сценарий 3: Распознавание речи с использованием словаря

```bash
# Распознаем аудио с использованием словаря сотрудника
curl -X POST http://localhost:5000/recognize \
  -F "file=@audio.mp3" \
  -F "api_key=YOUR_API_KEY" \
  -F "employee_id=ivanov"

# Результат:
# {
#   "text": "закажи молоко домик три упаковки",
#   "nomenclature_matches": [
#     {
#       "item_id": "n1a2b3c4",
#       "item_name": "Молоко Домик в деревне 3.2%",
#       "matched_as": "молоко домик",
#       "article": "MD-001"
#     }
#   ]
# }
```

## API Endpoints

### GET /employees
Получить список всех сотрудников.

```bash
curl http://localhost:5000/employees
```

**Ответ:**
```json
{
  "employees": [
    {
      "id": "ivanov",
      "name": "Иванов Иван Иванович",
      "email": "ivanov@example.com",
      "nomenclature_count": 315,
      "clients_count": 128
    }
  ]
}
```

### GET /employees/<id>
Получить полную информацию о сотруднике.

```bash
curl http://localhost:5000/employees/ivanov
```

### GET /employees/<id>/nomenclature
Получить номенклатуру сотрудника.

```bash
curl http://localhost:5000/employees/ivanov/nomenclature
```

### GET /employees/<id>/dictionary
Получить словарь для распознавания речи.

```bash
curl http://localhost:5000/employees/ivanov/dictionary
```

**Ответ:**
```json
{
  "employee_id": "ivanov",
  "dictionary": {
    "Молоко Домик в деревне 3.2%": [
      "Молоко Домик в деревне 3.2%",
      "MD-001",
      "12345",
      "молоко домик",
      "домик в деревне",
      "эм дэ ноль один"
    ]
  },
  "speechkit_format": "Молоко Домик в деревне 3.2%|MD-001,12345,молоко домик,домик в деревне,эм дэ ноль один",
  "total_terms": 315
}
```

### POST /recognize
Распознавание речи с использованием словаря сотрудника.

```bash
curl -X POST http://localhost:5000/recognize \
  -F "file=@audio.mp3" \
  -F "api_key=YOUR_API_KEY" \
  -F "employee_id=ivanov"
```

## Структура файлов данных

После импорта создаются файлы в папке `data/`:

### ivanov.json
```json
{
  "id": "ivanov",
  "name": "Иванов Иван Иванович",
  "email": "ivanov@example.com",
  "nomenclature": [
    {
      "id": "n1a2b3c4",
      "employee_id": "ivanov",
      "name": "Молоко Домик в деревне 3.2%",
      "article": "MD-001",
      "code": "12345",
      "voice_variants": [
        {
          "variant": "молоко домик",
          "original": "Молоко Домик в деревне 3.2%",
          "confidence": 1.0
        }
      ],
      "import_status": "success"
    }
  ],
  "clients": [
    {
      "id": "c1b2c3d4",
      "employee_id": "ivanov",
      "name": "ООО Ромашка",
      "code": "CL-001",
      "import_status": "success"
    }
  ]
}
```

## Голосовые варианты

### Зачем нужны?

Сотрудники часто используют сокращения и специфичные названия:
- "молоко домик" вместо "Молоко Домик в деревне 3.2%"
- "эм дэ ноль один" вместо артикула "MD-001"
- "ромашка" вместо "ООО Ромашка"

### Как добавлять?

```bash
# Добавить вариант произношения
python manage_voice_variants.py ivanov add n1a2b3c4 "молоко домик"

# Добавить с уверенностью (0.0 - 1.0)
python manage_voice_variants.py ivanov add n1a2b3c4 "домик" 0.8
```

### Формат словаря SpeechKit

```
Молоко Домик в деревне 3.2%|MD-001,12345,молоко домик,домик в деревне
Хлеб Бородинский|HB-002,бородинский,черный хлеб
```

Формат: `оригинальное_название|вариант1,вариант2,вариант3`

## Использование в Яндекс SpeechKit

Яндекс SpeechKit поддерживает пользовательские словари для улучшения распознавания.

### Вариант 1: Передача словаря в API

```python
import requests

# Получаем словарь сотрудника
response = requests.get('http://localhost:5000/employees/ivanov/dictionary')
dictionary = response.json()['speechkit_format']

# Отправляем на распознавание с словарем
with open('audio.mp3', 'rb') as f:
    audio_data = f.read()

response = requests.post(
    'https://stt.api.cloud.yandex.net/speech/v1/stt:recognize',
    params={
        'topic': 'general',
        'lang': 'ru-RU',
        'format': 'lpcm',
        'sampleRateHertz': '16000',
        'speechkit_dictionary': dictionary  # Передаем словарь
    },
    headers={'Authorization': f'Api-Key {API_KEY}'},
    data=audio_data
)
```

### Вариант 2: Постобработка результата

```python
# Распознаем без словаря
result = recognize_speech(audio_data)
text = result['text']

# Ищем совпадения с номенклатурой
matches = []
for item in employee.nomenclature:
    all_names = item.get_all_voice_names()
    for name in all_names:
        if name.lower() in text.lower():
            matches.append({
                'item': item,
                'matched_as': name
            })
            break
```

## Команды

### Импорт данных

```bash
# Импорт номенклатуры
python import_nomenclature_v2.py <employee_id> <file.xlsx>

# Импорт клиентов
python import_clients_v2.py <employee_id> <file.xlsx>
```

### Управление голосовыми вариантами

```bash
# Список номенклатуры
python manage_voice_variants.py <employee_id> list

# Добавить вариант
python manage_voice_variants.py <employee_id> add <item_id> <variant> [confidence]

# Экспорт словаря
python manage_voice_variants.py <employee_id> export

# Экспорт в формате SpeechKit
python manage_voice_variants.py <employee_id> speechkit
```

### API запросы

```bash
# Список сотрудников
curl http://localhost:5000/employees

# Информация о сотруднике
curl http://localhost:5000/employees/ivanov

# Номенклатура сотрудника
curl http://localhost:5000/employees/ivanov/nomenclature

# Словарь для распознавания
curl http://localhost:5000/employees/ivanov/dictionary

# Распознавание с использованием словаря
curl -X POST http://localhost:5000/recognize \
  -F "file=@audio.mp3" \
  -F "api_key=YOUR_KEY" \
  -F "employee_id=ivanov"
```

## Примеры голосовых вариантов

### Для номенклатуры

| Оригинальное название | Голосовые варианты |
|----------------------|-------------------|
| Молоко Домик в деревне 3.2% | молоко домик, домик в деревне, эм дэ ноль один |
| Хлеб Бородинский | бородинский, черный хлеб, бородинка |
| Масло сливочное 82% | сливочное масло, масло восемьдесят два |

### Для клиентов

| Оригинальное название | Голосовые варианты |
|----------------------|-------------------|
| ООО Ромашка | ромашка, ооо ромашка |
| ИП Иванов И.И. | иванов, ип иванов |
| Магазин "Продукты" | продукты, магазин продукты |

## Структура проекта

```
backend/
├── models.py                      # Модели данных (Employee, Nomenclature, Client)
├── import_nomenclature_v2.py      # Импорт номенклатуры с привязкой к сотруднику
├── import_clients_v2.py           # Импорт клиентов с привязкой к сотруднику
├── manage_voice_variants.py       # Управление голосовыми вариантами
├── server.py                      # Flask сервер с API
└── data/                          # Данные сотрудников (JSON файлы)
    ├── ivanov.json
    ├── petrov.json
    └── ...
```

## Зависимости

```bash
pip install openpyxl flask flask-cors requests
```

## Следующие шаги

1. ✅ Импортировать номенклатуру для сотрудников
2. ✅ Импортировать клиентов для сотрудников
3. ✅ Добавить голосовые варианты для номенклатуры
4. ⏳ Настроить интеграцию с Яндекс SpeechKit
5. ⏳ Создать веб-интерфейс для управления сотрудниками
6. ⏳ Добавить автоматическое обучение голосовых вариантов

## Поддержка

Если возникли проблемы:
1. Проверьте логи в консоли
2. Проверьте структуру JSON файлов в `data/`
3. Убедитесь что все зависимости установлены
4. Пришлите ошибку и контекст
