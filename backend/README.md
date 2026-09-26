# Бэкенд voice2price

Flask, порт 5000. Распознаёт голосовые сообщения, разбирает их в заказ по справочнику филиала,
хранит справочники филиалов.

## Стандарт

- **API**: все эндпоинты под `/api/`, JSON в ответе, ошибка — `{"error": "..."}` с кодом 4xx/5xx.
  Ресурсы во множественном числе и вложены в филиал: `/api/employees/<id>/nomenclature`,
  `…/dictionary/variants/<variant_id>`. Создание — `POST` на коллекцию, удаление — `DELETE` на элемент.
  Параметры запросов в `snake_case`. Полный список печатается при старте сервера.
- **Хранение**: все данные — в PostgreSQL. Схема одна — `models_db.py`; при старте `init_db()`
  создаёт таблицы, недостающие колонки и индексы. Доступ к данным — через `repositories.py`.
  Redis — только кэш словаря произношений (`database.DictionaryCache`); без него всё читается из БД.
  Ключи Яндекс Облака хранятся в таблице `yandex_cloud_settings` и в запросах не передаются.
- «Сотрудник» (`employees`) в интерфейсе называется «Филиал».

## Модули

| Модуль | Что делает |
|---|---|
| `server.py` | распознавание, разбор заказа, анализ аудио и XLSX |
| `api_employees.py` | филиалы, номенклатура, клиенты, словарь, единицы, настройки разбора |
| `api_yandex_cloud.py` | настройки Яндекс Облака, готовность движков (`/api/engines`) |
| `models_db.py`, `repositories.py`, `database.py` | схема, доступ к данным, подключения |
| `import_nomenclature.py`, `import_clients.py` | импорт XLSX из 1С; повторный импорт без дублей (`catalog_sync.py`) |
| `order_pipeline.py` | разбор заказа правилами: сегменты → кандидаты → проверенный выбор |
| `order_segmenter.py`, `spoken_quantity.py` | нарезка расшифровки на позиции, количества словами |
| `catalog_matching.py` | поиск кандидатов по названию (зафиксирован бенчмарком 2026-09-23) |
| `client_matching.py` | клиент по началу сообщения и словарю |
| `order_merging.py` | склейка подряд идущих голосовых одного клиента |
| `order_settings.py` | опции разбора филиала |
| `catalog_validation.py`, `branch_data.py` | проверка справочника; данные филиала для разбора |
| `order_parser.py`, `order_prompts.py` | прежний разбор через YandexGPT (`parser=llm`) |
| `gigaam_client.py`, `audio_preparation.py` | локальное распознавание GigaAM; подготовка аудио для SpeechKit |

## API

| Метод | Путь | |
|---|---|---|
| GET | `/api/health` | проверка работоспособности |
| GET | `/api/engines` | готовность распознавания (`gigaam`, `speechkit`) и разбора (`rules`, `llm`) |
| POST | `/api/recognize` | form: `file`, `engine`, `employee_id`, `process_llm`, `parser` → текст, сегменты, клиент, позиции |
| POST | `/api/process-order` | `{text, employee_id, parser}` → `{order_items, client}` |
| POST | `/api/process-orders` | `{employee_id, parser, messages: [{id, file_name, text, last_modified}]}` → заказы со склейкой |
| POST | `/api/detect-client` | `{employee_id, text}` → `{client}` |
| POST | `/api/analyze` | form: `file` → длительность, формат аудио |
| POST | `/api/analyze-xlsx` | form: `file` → листы, колонки, примеры |
| GET, POST | `/api/employees` | список / создание филиала |
| GET, PUT, DELETE | `/api/employees/<id>` | филиал |
| GET, PUT | `/api/employees/<id>/order-settings` | опции разбора |
| GET | `/api/employees/<id>/nomenclature` | номенклатура с вариантами произношения |
| POST | `/api/employees/<id>/nomenclature/import` | импорт XLSX |
| GET | `/api/employees/<id>/nomenclature/validation` | позиции, которые голосом не различить |
| PUT | `/api/employees/<id>/nomenclature/<nomenclature_id>/limit` | реалистичный максимум в заказе |
| GET | `/api/employees/<id>/clients` | клиенты, как их можно назвать, конфликты сокращений |
| POST | `/api/employees/<id>/clients/import` | импорт XLSX |
| GET, POST | `/api/employees/<id>/dictionary` | словарь произношений / добавить вариант `{original, variant, category, item_id}` |
| DELETE | `/api/employees/<id>/dictionary/variants/<variant_id>` | удалить вариант |
| GET, POST | `/api/employees/<id>/units` | единицы измерения |
| POST | `/api/employees/<id>/units/<unit_id>/variants` | вариант произношения единицы |
| DELETE | `/api/employees/<id>/units/<unit_id>/variants/<variant_id>` | удалить вариант |
| GET | `/api/employees/<id>/orders` | сохранённые заказы |
| GET, POST, DELETE | `/api/yandex-cloud/settings` | настройки Яндекс Облака (секреты не возвращаются) |
| POST | `/api/yandex-cloud/test-connection` | `{service: speechkit\|yandexgpt}` |

## Переменные окружения

`DATABASE_URL`, `REDIS_URL`; `STT_ENGINE` (`gigaam` | `speechkit`), `ORDER_PARSER` (`rules` | `llm`);
`GIGAAM_URL`, `GIGAAM_MODEL`. Значения по умолчанию — в `docker-compose.yml`.

## Импорт без интерфейса

```bash
docker exec audio-analyzer-backend python import_nomenclature.py <employee_id> файл.xlsx
docker exec audio-analyzer-backend python import_clients.py <employee_id> файл.xlsx
# файл сначала скопировать в контейнер: docker cp файл.xlsx audio-analyzer-backend:/app/
```

## Тесты

```bash
docker compose up -d --build backend
docker exec audio-analyzer-backend sh -c "cd /app && python -m unittest discover -p 'test_*.py'"
```
