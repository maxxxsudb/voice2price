# Настройка интеграции с Яндекс Облаком

## Обзор

Этот модуль позволяет хранить и управлять настройками Яндекс Облака через базу данных:
- **JSON-ключ сервисного аккаунта** - для получения IAM токенов
- **Folder ID** - для использования SpeechKit
- **Object Storage настройки** - бакет, access key, secret key
- **IAM токен** - автоматически обновляется при истечении

## API Endpoints

### 1. Получить текущие настройки
```http
GET /yandex-cloud/settings
```

Ответ:
```json
{
  "settings": {
    "id": 1,
    "folder_id": "b1gxxxxxxxx",
    "bucket_name": "my-audio-bucket",
    "endpoint": "https://storage.yandexcloud.net",
    "access_key_id": "YCAB...",
    "has_service_account_key": true,
    "has_secret_access_key": true,
    "iam_token_valid": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
}
```

### 2. Сохранить настройки
```http
POST /yandex-cloud/settings
Content-Type: application/json

{
  "service_account_key": "{...}",  // JSON-ключ сервисного аккаунта
  "folder_id": "b1gxxxxxxxx",
  "bucket_name": "my-audio-bucket",
  "endpoint": "https://storage.yandexcloud.net",
  "access_key_id": "YCAB...",
  "secret_access_key": "..."
}
```

### 3. Удалить настройки
```http
DELETE /yandex-cloud/settings
```

### 4. Сгенерировать IAM токен
```http
POST /yandex-cloud/iam-token
```

Ответ:
```json
{
  "message": "IAM токен успешно получен",
  "iam_token": "t1.9e...",
  "expires_at": "2024-01-01T01:00:00+00:00",
  "valid_for_seconds": 3600
}
```

### 5. Получить IAM токен (с автообновлением)
```http
GET /yandex-cloud/iam-token
```

Если токен действителен - вернётся из кэша. Если истёк - будет сгенерирован новый.

### 6. Тестирование подключения
```http
POST /yandex-cloud/test-connection
```

Ответ:
```json
{
  "status": "ok",
  "checks": {
    "service_account_key": "✅ Настроен",
    "folder_id": "✅ b1gxxxxxxxx",
    "object_storage": "✅ Бакет: my-audio-bucket",
    "iam_token": "✅ Действителен (3500 сек)"
  }
}
```

### 7. Тестирование получения IAM-токена (из фронтенда)
```http
POST /yandex-cloud/test-token
Content-Type: application/json

{
  "service_account_key": "{...}",
  "folder_id": "b1gxxxxxxxx"
}
```

Этот endpoint используется для тестирования настроек прямо из интерфейса без сохранения в базу данных.

Ответ:
```json
{
  "success": true,
  "message": "IAM-токен успешно получен",
  "iamToken": "t1.9e...",
  "expiresIn": 3600,
  "expiresAt": "2024-01-01T01:00:00+00:00",
  "folderId": "b1gxxxxxxxx"
}
```

## Как использовать в интерфейсе

### Шаг 1: Создать сервисный аккаунт в Яндекс Облаке

1. Перейти в [Консоль управления](https://console.cloud.yandex.ru/)
2. Выбрать нужный каталог
3. Создать сервисный аккаунт с ролью `editor` или `ai.languageModels.user`
4. Создать ключ для сервисного аккаунта:
   - Выберите сервисный аккаунт
   - Нажмите "Создать новый ключ"
   - Выберите тип ключа "JSON"
   - Скачайте файл ключа

### Шаг 2: Ввести настройки в интерфейс

В интерфейсе приложения должна быть форма с полями:

#### JSON-ключ сервисного аккаунта (обязательно)
- Скопируйте содержимое скачанного JSON файла
- Вставьте в поле ввода (текстовое поле или загрузка файла)

Пример JSON-ключа:
```json
{
  "id": "aje...",
  "subject_token_audience": "urn:ietf:params:oauth:token-type:jwt",
  "key_id": "mzj...",
  "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n",
  "public_key": "...",
  "service_account_id": "ajg..."
}
```

#### Folder ID (рекомендуется)
- Получите в консоли Яндекс Облака
- Формат: `b1gxxxxxxxxxxxxxxx`

#### Object Storage (опционально)
Для работы с большими файлами через Object Storage:

- **Имя бакета**: `my-audio-files`
- **Access Key ID**: `YCAB...`
- **Secret Access Key**: `...`

### Шаг 3: Проверка подключения

Нажмите кнопку "Проверить подключение" - система проверит:
- ✅ Наличие JSON-ключа
- ✅ Валидность Folder ID
- ✅ Настройки Object Storage
- ✅ Работоспособность IAM токена

### Шаг 4: Автоматическое получение IAM токена

После сохранения JSON-ключа:
- IAM токен генерируется автоматически при необходимости
- Токен хранится в базе данных
- При истечении токена (< 1 минуты) он автоматически обновляется

## Интеграция с распознаванием речи

При использовании асинхронного API SpeechKit теперь можно использовать IAM токен из БД:

```python
# Пример использования в server.py
from repositories import YandexCloudSettingsRepository

settings = YandexCloudSettingsRepository.get_settings()
if settings and settings.is_iam_token_valid():
    iam_token = settings.iam_token
    # Использовать iam_token вместо api_key
    headers = {'Authorization': f'Bearer {iam_token}'}
else:
    # Использовать старый метод с api_key из формы
    api_key = request.form.get('api_key', '')
```

## Безопасность

- JSON-ключ сервисного аккаунта хранится в базе данных в зашифрованном виде (рекомендуется добавить шифрование)
- Secret Access Key не возвращается в API ответах
- IAM токен автоматически обновляется при истечении
- Все чувствительные данные передаются только по HTTPS

## Требования

Установите необходимые зависимости:
```bash
pip install PyJWT>=2.8.0
```

## Troubleshooting

### Ошибка: "В JSON-ключе отсутствует private_key"
Убедитесь что скопировали полный JSON-ключ включая приватный ключ.

### Ошибка: "Невалидный JSON"
JSON-ключ должен быть валидным JSON объектом. Проверьте формат.

### Ошибка: "Ошибка получения IAM токена: 401"
Сервисный аккаунт не имеет необходимых прав. Добавьте роль `editor` или `ai.languageModels.user`.

### IAM токен быстро истекает
Это нормально - время жизни IAM токена 1 час. Система автоматически обновляет его при необходимости.
