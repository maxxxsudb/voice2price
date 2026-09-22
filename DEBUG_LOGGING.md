# Логирование и отладка

## Что добавлено

Добавлено подробное логирование на всех уровнях:

### Бэкенд (Python)
- Логи при старте сервера
- Логи при каждом запросе (health, recognize, analyze, analyze-xlsx)
- Логи при обработке файлов
- Логи ошибок с traceback
- Логи при удалении временных файлов

### Фронтенд (React)
- Логи при выборе файла
- Логи при отправке запроса
- Логи при получении ответа
- Логи при парсинге JSON
- Логи при рендере результата
- Логи при копировании

## Как смотреть логи

### 1. Логи бэкенда (в терминале Docker)

```bash
# Смотреть все логи
docker compose logs -f

# Только логи бэкенда
docker compose logs -f backend

# Последние 100 строк
docker compose logs --tail=100 backend
```

Пример вывода:
```
======================================================================
📊 [XLSX ANALYZE] Начало анализа файла
======================================================================
✅ [XLSX ANALYZE] Получен файл: nomenclature.xlsx
💾 [XLSX ANALYZE] Файл сохранён: /tmp/tmp123.xlsx
📦 [XLSX ANALYZE] Импортируем модуль analyze_xlsx...
✅ [XLSX ANALYZE] Модуль успешно импортирован
🔍 [XLSX ANALYZE] Начинаем анализ файла...

🔍 [XLSX MODULE] Начинаем анализ файла: /tmp/tmp123.xlsx
✅ [XLSX MODULE] Файл существует, размер: 15360 байт
📖 [XLSX MODULE] Загружаем workbook...
✅ [XLSX MODULE] Workbook загружен, листов: 1

📄 [XLSX MODULE] Анализируем лист 1/1: Sheet1
   Строк: 100, Колонок: 5
   🔍 Читаем заголовки...
   ✅ Заголовков: 5
   🔍 Анализируем колонки...
      A: Артикул [string] (98 значений)
      B: Название [string] (100 значений)
      C: Цена [number] (95 значений)
      D: Категория [string] (80 значений)
      E: Описание [string] (60 значений)
   🔍 Собираем примеры строк...
   ✅ Примеров строк: 3

✅ [XLSX MODULE] Анализ завершён, листов обработано: 1
✅ [XLSX ANALYZE] Анализ завершён успешно
   Найдено листов: 1
   Лист 1: Sheet1 (100 строк × 5 колонок)
======================================================================
✅ [XLSX ANALYZE] Возвращаем результат клиенту
======================================================================
```

### 2. Логи фронтенда (в консоли браузера)

1. Откройте браузер
2. Нажмите F12 (или правая кнопка → Inspect)
3. Перейдите на вкладку **Console**
4. Загрузите файл

Пример вывода:
```
======================================================================
📊 [FRONTEND] Начало анализа XLSX файла
======================================================================
📁 [FRONTEND] Выбран файл: nomenclature.xlsx
📏 [FRONTEND] Размер: 0.01 МБ
🔗 [FRONTEND] URL бэкенда: http://localhost:5000/analyze-xlsx
📤 [FRONTEND] Формируем FormData...
✅ [FRONTEND] FormData сформирован
🚀 [FRONTEND] Отправляем запрос на бэкенд...
⏱️  [FRONTEND] Запрос выполнен за 1234мс
📥 [FRONTEND] Статус ответа: 200 OK
📥 [FRONTEND] Парсим JSON ответ...
✅ [FRONTEND] JSON успешно распарсен
📊 [FRONTEND] Получено данных: {
  file: "/tmp/tmp123.xlsx",
  file_size_mb: 0.01,
  sheets_count: 1
}
   📄 Лист 1: Sheet1 (100 строк × 5 колонок)
💾 [FRONTEND] Сохраняем результат в state...
✅ [FRONTEND] Результат сохранён
======================================================================
```

## Частые проблемы

### 1. Экран пропадает после загрузки

**Симптомы:**
- Крутится колёсико 5 секунд
- Экран становится пустым

**Причины:**
- Бэкенд упал с ошибкой
- CORS ошибка
- Ошибка при рендере результата

**Решение:**
1. Посмотрите логи бэкенда: `docker compose logs -f backend`
2. Посмотрите логи фронтенда: F12 → Console
3. Проверьте что бэкенд запущен: `curl http://localhost:5000/health`

### 2. Ошибка "Failed to fetch"

**Причина:** Бэкенд не запущен или недоступен

**Решение:**
```bash
# Проверить что бэкенд запущен
docker compose ps

# Перезапустить бэкенд
docker compose restart backend

# Посмотреть логи
docker compose logs -f backend
```

### 3. Ошибка CORS

**Симптомы:**
```
Access to fetch at 'http://localhost:5000/analyze-xlsx' from origin 
'http://localhost:3000' has been blocked by CORS policy
```

**Решение:**
Убедитесь что в `backend/server.py` есть:
```python
from flask_cors import CORS
CORS(app)
```

### 4. Ошибка импорта модуля

**Симптомы:**
```
❌ [XLSX ANALYZE] Ошибка импорта модуля: No module named 'openpyxl'
```

**Решение:**
```bash
# Пересобрать контейнер
docker compose down
docker compose up --build
```

### 5. Пустой результат

**Симптомы:**
- Анализ завершился успешно
- Но результат пустой

**Решение:**
1. Проверьте логи бэкенда - возможно файл повреждён
2. Проверьте логи фронтенда - возможно ошибка при рендере
3. Попробуйте другой XLSX файл

## Отладка

### Включить debug режим

В `docker-compose.yml` уже включён debug режим для Flask:
```yaml
environment:
  - FLASK_ENV=development
  - FLASK_DEBUG=1
```

### Смотреть все запросы

```bash
# Все логи в реальном времени
docker compose logs -f

# Только ошибки
docker compose logs -f | grep -i error

# Только XLSX
docker compose logs -f | grep -i xlsx
```

### Проверить бэкенд вручную

```bash
# Health check
curl http://localhost:5000/health

# Анализ XLSX
curl -X POST http://localhost:5000/analyze-xlsx \
  -F "file=@nomenclature.xlsx"
```

### Войти в контейнер

```bash
# Войти в бэкенд
docker compose exec backend bash

# Проверить файлы
ls -la /app

# Проверить Python
python --version

# Проверить зависимости
pip list

# Выйти
exit
```

## Логи при ошибках

При ошибках логи содержат:
- Полный traceback
- Номер строки где произошла ошибка
- Текст ошибки
- Контекст (что делали до ошибки)

Пример:
```
❌ [XLSX ANALYZE] КРИТИЧЕСКАЯ ОШИБКА: Invalid file format
Traceback (most recent call last):
  File "/app/server.py", line 123, in analyze_xlsx
    result = analyze_file(tmp_path)
  File "/app/analyze_xlsx.py", line 45, in analyze_xlsx
    wb = openpyxl.load_workbook(file_path)
  File "/usr/local/lib/python3.11/site-packages/openpyxl/reader/excel.py", line 315
    raise InvalidFileException(
openpyxl.utils.exceptions.InvalidFileException: Invalid file format
```

## Поддержка

Если проблема не решается:
1. Скопируйте полные логи бэкенда
2. Скопируйте полные логи фронтенда (Console)
3. Опишите что делали
4. Приложите скриншот ошибки
