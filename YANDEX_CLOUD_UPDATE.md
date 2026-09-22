# Настройки Яндекс Облака — Обновление

## ✅ Выполненные изменения

### 1. Фронтенд (`src/components/YandexCloudSettings.tsx`)

**Добавлено:**
- Кнопка **"Сохранить и протестировать"** с иконкой `Save`
- Сохранение всех параметров в БД через API `/api/yandex-cloud/settings`
- Тестирование получения IAM-токена через API `/api/yandex-cloud/test-token`
- Индикация статуса сохранения и тестирования
- Улучшенные сообщения об ошибках с эмодзи

**Поля для ввода:**
- ✅ Приватный ключ (JSON-ключ сервисного аккаунта) — обязательное
- ✅ Folder ID — обязательное
- ✅ Имя бакета (Object Storage) — опционально
- ✅ Access Key ID — опционально
- ✅ Secret Access Key — опционально

### 2. Бэкенд (`backend/api_yandex_cloud.py`)

**Существующие endpoint'ы:**
```python
POST /api/yandex-cloud/settings      # Сохранить настройки в БД
GET  /api/yandex-cloud/settings      # Получить настройки из БД
POST /api/yandex-cloud/test-token    # Протестировать получение IAM-токена
POST /api/yandex-cloud/iam-token     # Сгенерировать новый IAM-токен
GET  /api/yandex-cloud/iam-token     # Получить текущий IAM-токен
POST /api/yandex-cloud/test-connection # Протестировать подключение
```

**Репозиторий (`backend/repositories.py`):**
```python
YandexCloudSettingsRepository.create_or_update(data)  # Создать/обновить настройки
YandexCloudSettingsRepository.get_settings()          # Получить настройки
YandexCloudSettingsRepository.update_iam_token()      # Обновить IAM-токен
```

**Модель (`backend/models_db.py`):**
```python
class YandexCloudSettings(Base):
    service_account_key       # JSON-ключ сервисного аккаунта
    folder_id                 # Folder ID для SpeechKit
    bucket_name               # Имя бакета Object Storage
    access_key_id             # Access Key для S3
    secret_access_key         # Secret Key для S3
    iam_token                 # Текущий IAM-токен
    iam_token_expires_at      # Время истечения токена
```

## 📋 Процесс работы кнопки "Сохранить и протестировать"

1. **Валидация данных:**
   - Проверка наличия JSON-ключа
   - Проверка наличия Folder ID
   - Валидация формата JSON

2. **Сохранение в БД:**
   ```javascript
   POST http://localhost:5000/api/yandex-cloud/settings
   Body: {
     serviceAccountKey: "...",
     folderId: "b1g...",
     bucketName: "...",
     accessKeyId: "...",
     secretAccessKey: "..."
   }
   ```

3. **Тестирование IAM-токена:**
   ```javascript
   POST http://localhost:5000/api/yandex-cloud/test-token
   Body: {
     serviceAccountKey: "...",
     folderId: "b1g..."
   }
   ```

4. **Отображение результата:**
   - ✅ Успех: "Настройки сохранены в БД. IAM-токен успешно получен!"
   - ⚠️ Частичный успех: "Настройки сохранены, но ошибка получения токена"
   - ❌ Ошибка: Сообщение об ошибке

## 🔐 Безопасность

- JSON-ключ хранится в базе данных (рекомендуется шифрование)
- IAM-токен автоматически обновляется при истечении (срок жизни 3 часа)
- Secret Key показывается только при нажатии кнопки "Показать"
- Данные передаются по HTTPS (в продакшене)

## 🧪 Тестирование

### Проверка фронтенда:
```bash
cd /workspace
npm run build
# Сборка успешна ✅
```

### Проверка бэкенда:
```bash
cd /workspace/backend
python3 -c "from api_yandex_cloud import yandex_cloud_bp; print('✅')"
python3 -c "from repositories import YandexCloudSettingsRepository; print('✅')"
```

## 📝 Инструкция для пользователя

1. Откройте вкладку **"Яндекс Облако"**
2. Вставьте JSON-ключ сервисного аккаунта
3. Укажите Folder ID (начинается с `b1g`)
4. (Опционально) Настройте Object Storage
5. Нажмите **"Сохранить и протестировать"**
6. Проверьте результат теста

## 🔄 Отличия от старой системы

| Параметр | Старая (API-ключ) | Новая (Яндекс Облако) |
|----------|-------------------|-----------------------|
| Хранение | localStorage | База данных ✅ |
| Аутентификация | Api-Key заголовок | Bearer IAM-токен ✅ |
| Срок действия | Бессрочно | 3 часа (автообновление) ✅ |
| Object Storage | ❌ Не поддерживался | ✅ Полная поддержка |
| Тестирование | ❌ Нет | ✅ Встроенное ✅ |

## 📄 Дополнительные файлы

- `YANDEX_CLOUD_SETTINGS.md` — Подробная документация
- `src/types.ts` — Интерфейс `YandexCloudConfig`
- `src/App.tsx` — Интеграция вкладки в приложение
