"""
API endpoints для работы с настройками Яндекс Облака (Object Storage, IAM, сервисный аккаунт).
Все настройки хранятся в базе данных.
"""

import json
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from repositories import YandexCloudSettingsRepository

yandex_cloud_bp = Blueprint('yandex_cloud', __name__)
import logging
logger = logging.getLogger(__name__)


def _extract_sa_credentials(settings_or_none, override_key=None, override_sa_id=None):
    """
    Извлечь (key_id, service_account_id, private_key) из настроек.
    Поддерживает JSON-ключ и PEM-ключ + отдельное поле service_account_id.
    Возвращает tuple или выбрасывает ValueError с человекочитаемым сообщением.
    """
    raw = override_key
    sa_id_manual = override_sa_id
    if raw is None:
        if not settings_or_none:
            raise ValueError('Настройки Яндекс Облака не найдены. Сохраните настройки на вкладке "Яндекс Облако".')
        raw = settings_or_none.service_account_key or ''
        sa_id_manual = settings_or_none.service_account_id

    raw = (raw or '').strip()
    if not raw:
        raise ValueError('Ключ сервисного аккаунта не настроен. Пожалуйста, сохраните настройки.')

    if raw.startswith('{'):
        try:
            key_data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f'Невалидный JSON-ключ сервисного аккаунта: {e}')
        key_id = key_data.get('id')
        service_account_id = sa_id_manual or key_data.get('service_account_id')
        private_key = key_data.get('private_key')
    elif 'BEGIN' in raw and 'PRIVATE KEY' in raw:
        key_id = None
        service_account_id = (sa_id_manual or '').strip() or None
        private_key = raw.replace('\r\n', '\n')
    else:
        raise ValueError('Неизвестный формат ключа. Ожидается JSON-файл сервисного аккаунта или PEM-ключ (-----BEGIN PRIVATE KEY-----).')

    if not service_account_id:
        raise ValueError('Не указан ID сервисного аккаунта (aje...). Заполните поле "ID сервисного аккаунта".')
    if not private_key:
        raise ValueError('Отсутствует приватный ключ (private_key).')

    # Для PEM-ключа kid можно не указывать — Яндекс определяет его сам
    return key_id, service_account_id, private_key



@yandex_cloud_bp.route('/yandex-cloud/settings', methods=['GET'])
def get_settings():
    """Получить текущие настройки Яндекс Облака"""
    try:
        settings = YandexCloudSettingsRepository.get_settings()
        
        if not settings:
            return jsonify({
                'settings': None,
                'message': 'Настройки не найдены. Пожалуйста, настройте интеграцию.'
            })
        
        return jsonify({'settings': settings.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@yandex_cloud_bp.route('/yandex-cloud/settings', methods=['POST'])
def save_settings():
    """
    Сохранить настройки Яндекс Облака в БД.

    Принимает JSON (camelCase или snake_case):
    {
        "serviceAccountKey": "...",   // JSON-ключ ИЛИ PEM-приватный ключ сервисного аккаунта
        "serviceAccountId": "aje...", // ID сервисного аккаунта (обязателен в PEM-режиме)
        "folderId": "b1g...",         // Folder ID для SpeechKit
        "bucketName": "my-bucket",    // Имя бакета Object Storage
        "accessKeyId": "YCAJE...",    // S3 access key
        "secretAccessKey": "..."      // S3 secret key
    }
    """
    try:
        data = request.json or {}

        # Нормализуем camelCase -> snake_case
        mapping = {
            'serviceAccountKey': 'service_account_key',
            'serviceAccountId': 'service_account_id',
            'apiKey': 'api_key',
            'folderId': 'folder_id',
            'bucketName': 'bucket_name',
            'accessKeyId': 'access_key_id',
            'secretAccessKey': 'secret_access_key',
            'endpoint': 'endpoint',
        }
        normalized = {}
        for src_key, dst_key in mapping.items():
            if src_key in data:
                normalized[dst_key] = data[src_key]
        # Пропускаем уже snake_case поля
        for dst_key in mapping.values():
            if dst_key in data:
                normalized[dst_key] = data[dst_key]

        sa_key = (normalized.get('service_account_key') or '').strip()
        sa_id = (normalized.get('service_account_id') or '').strip()

        if not sa_key and not sa_id and not normalized.get('folder_id'):
            return jsonify({'error': 'Пустой запрос: не передано ни одного поля настроек'}), 400

        # Валидация и автоизвлечение полей из ключа
        if sa_key.startswith('{'):
            # JSON-ключ сервисного аккаунта
            try:
                key_data = json.loads(sa_key)
            except json.JSONDecodeError as e:
                return jsonify({'error': f'Невалидный JSON в ключе сервисного аккаунта: {str(e)}'}), 400
            if not isinstance(key_data, dict):
                return jsonify({'error': 'Ключ сервисного аккаунта должен быть JSON объектом'}), 400
            missing = [f for f in ('id', 'service_account_id', 'private_key') if f not in key_data]
            if missing:
                return jsonify({
                    'error': 'В JSON-ключе отсутствуют поля: ' + ', '.join(missing) +
                             '. Убедитесь, что вы загрузили полный JSON-файл сервисного аккаунта Яндекс Облака.'
                }), 400
            # Автозаполняем service_account_id из JSON, если не задан вручную
            if not sa_id:
                normalized['service_account_id'] = key_data['service_account_id']
        elif 'BEGIN' in sa_key and 'PRIVATE KEY' in sa_key:
            # PEM-режим: service_account_id обязателен
            if not sa_id:
                return jsonify({
                    'error': 'Вы ввели приватный ключ (PEM). Укажите также ID сервисного аккаунта '
                             '(поле "ID сервисного аккаунта", начинается с aje) или вставьте полный JSON-ключ.'
                }), 400
        else:
            return jsonify({
                'error': 'Поле "Приватный ключ или JSON-ключ" должно содержать полный JSON-файл '
                         'сервисного аккаунта (начинается с "{") или PEM-ключ (-----BEGIN PRIVATE KEY-----).'
            }), 400

        settings = YandexCloudSettingsRepository.create_or_update(normalized)

        logger.info(f"✅ [YC] Настройки сохранены в БД (id={settings.id}, folder={settings.folder_id})")

        return jsonify({
            'message': 'Настройки сохранены в базе данных',
            'settings': settings.to_dict()
        }), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@yandex_cloud_bp.route('/yandex-cloud/settings', methods=['DELETE'])
def delete_settings():
    """Удалить настройки Яндекс Облака"""
    try:
        success = YandexCloudSettingsRepository.delete_settings()
        
        if success:
            return jsonify({'message': 'Настройки удалены'})
        else:
            return jsonify({'message': 'Настройки не найдены'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@yandex_cloud_bp.route('/yandex-cloud/iam-token', methods=['POST'])
def generate_iam_token():
    """
    Сгенерировать новый IAM токен используя JSON-ключ сервисного аккаунта.
    
    Этот endpoint получает JWT токен из JSON-ключа сервисного аккаунта
    и обменивает его на IAM токен через Яндекс API.
    """
    try:
        from jwt import encode
        import requests
        
        # Получаем настройки из БД
        settings = YandexCloudSettingsRepository.get_settings()
        
        try:
            key_id, service_account_id, private_key = _extract_sa_credentials(settings)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Создаем JWT токен
        now = datetime.now(timezone.utc)
        iat = int(now.timestamp())
        exp = int((now + timedelta(hours=1)).timestamp())
        
        payload = {
            'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            'iss': service_account_id,
            'iat': iat,
            'exp': exp
        }
        
        # Подписываем JWT приватным ключом
        jwt_headers = {'typ': 'JWT'}
        if key_id:
            jwt_headers['kid'] = key_id
        jwt_token = encode(
            payload,
            private_key,
            algorithm='PS256',
            headers=jwt_headers
        )
        
        # Обмениваем JWT на IAM токен
        iam_response = requests.post(
            'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            json={'jwt': jwt_token},
            timeout=30
        )
        
        if iam_response.status_code != 200:
            return jsonify({
                'error': f'Ошибка получения IAM токена: {iam_response.status_code}',
                'details': iam_response.text
            }), 400
        
        iam_data = iam_response.json()
        iam_token = iam_data.get('iamToken')
        expires_at = datetime.fromisoformat(iam_data.get('expiresAt').replace('Z', '+00:00'))
        
        # Сохраняем IAM токен в БД
        YandexCloudSettingsRepository.update_iam_token(iam_token, expires_at)
        
        return jsonify({
            'message': 'IAM токен успешно получен',
            'iam_token': iam_token,
            'expires_at': expires_at.isoformat(),
            'valid_for_seconds': int((expires_at - datetime.now(timezone.utc)).total_seconds())
        })
    except ImportError as e:
        return jsonify({
            'error': f'Отсутствует необходимая библиотека: {str(e)}. Установите: pip install PyJWT',
            'details': 'Для работы с IAM токенами требуется библиотека PyJWT'
        }), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@yandex_cloud_bp.route('/yandex-cloud/iam-token', methods=['GET'])
def get_iam_token():
    """
    Получить текущий IAM токен.
    Если токен истек или отсутствует - автоматически генерируем новый.
    """
    try:
        settings = YandexCloudSettingsRepository.get_settings()
        
        if not settings:
            return jsonify({
                'error': 'Настройки Яндекс Облака не найдены'
            }), 404
        
        if not settings.service_account_key:
            return jsonify({
                'error': 'Ключ сервисного аккаунта не настроен'
            }), 404
        
        # Проверяем валидность текущего токена
        if settings.is_iam_token_valid():
            return jsonify({
                'iam_token': settings.iam_token,
                'expires_at': settings.iam_token_expires_at.isoformat(),
                'from_cache': True
            })
        
        # Токен истек - генерируем новый
        print("ℹ️  [IAM] Текущий токен истек, генерируем новый...")
        
        # Вызываем endpoint генерации токена
        from jwt import encode
        import requests
        from datetime import datetime, timezone, timedelta
        
        try:
            key_id, service_account_id, private_key = _extract_sa_credentials(settings)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        now = datetime.now(timezone.utc)
        iat = int(now.timestamp())
        exp = int((now + timedelta(hours=1)).timestamp())
        
        payload = {
            'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            'iss': service_account_id,
            'iat': iat,
            'exp': exp
        }
        
        jwt_headers = {'typ': 'JWT'}
        if key_id:
            jwt_headers['kid'] = key_id
        jwt_token = encode(
            payload,
            private_key,
            algorithm='PS256',
            headers=jwt_headers
        )
        
        iam_response = requests.post(
            'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            json={'jwt': jwt_token},
            timeout=30
        )
        
        if iam_response.status_code != 200:
            return jsonify({
                'error': f'Ошибка получения IAM токена: {iam_response.status_code}'
            }), 400
        
        iam_data = iam_response.json()
        iam_token = iam_data.get('iamToken')
        expires_at = datetime.fromisoformat(iam_data.get('expiresAt').replace('Z', '+00:00'))
        
        # Сохраняем новый токен
        YandexCloudSettingsRepository.update_iam_token(iam_token, expires_at)
        
        return jsonify({
            'iam_token': iam_token,
            'expires_at': expires_at.isoformat(),
            'from_cache': False,
            'message': 'Токен обновлен'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@yandex_cloud_bp.route('/yandex-cloud/test-connection', methods=['POST'])
def test_connection():
    """
    Протестировать подключение к Яндекс Облаку.
    Проверяет валидность настроек и возможность получения IAM токена.
    """
    try:
        settings = YandexCloudSettingsRepository.get_settings()
        
        if not settings:
            return jsonify({
                'status': 'error',
                'message': 'Настройки не найдены'
            }), 404
        
        result = {
            'status': 'ok',
            'checks': {}
        }
        
        # Проверка 1: Наличие JSON-ключа
        if settings.service_account_key:
            result['checks']['service_account_key'] = '✅ Настроен'
        else:
            result['checks']['service_account_key'] = '❌ Не настроен'
            result['status'] = 'warning'
        
        # Проверка 2: Folder ID
        if settings.folder_id:
            result['checks']['folder_id'] = f'✅ {settings.folder_id}'
        else:
            result['checks']['folder_id'] = '⚠️ Не указан (необязательно)'
        
        # Проверка 3: Object Storage настройки
        if settings.bucket_name and settings.access_key_id:
            result['checks']['object_storage'] = f'✅ Бакет: {settings.bucket_name}'
        else:
            result['checks']['object_storage'] = '⚠️ Не настроен (необязательно)'
        
        # Проверка 4: IAM токен
        if settings.is_iam_token_valid():
            expires_in = int((settings.iam_token_expires_at - datetime.now(timezone.utc)).total_seconds())
            result['checks']['iam_token'] = f'✅ Действителен ({expires_in} сек)'
        else:
            result['checks']['iam_token'] = '⚠️ Отсутствует или истек'
            result['status'] = 'warning'
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@yandex_cloud_bp.route('/yandex-cloud/test-token', methods=['POST'])
def test_token():
    """
    Протестировать получение IAM-токена с переданными параметрами.
    Используется для тестирования из фронтенда без сохранения в БД.
    
    Принимает JSON:
    {
        "service_account_key": "{...}",
        "folder_id": "b1g..."
    }
    """
    try:
        from jwt import encode
        import requests
        
        data = request.json
        if not data:
            return jsonify({'error': 'Требуется JSON тело запроса'}), 400
        
        service_account_key = data.get('service_account_key') or data.get('serviceAccountKey')
        service_account_id_manual = data.get('service_account_id') or data.get('serviceAccountId')
        folder_id = data.get('folder_id') or data.get('folderId')

        if not service_account_key:
            return jsonify({'error': 'Не указан ключ сервисного аккаунта'}), 400
        if not folder_id:
            return jsonify({'error': 'Не указан folder_id'}), 400

        try:
            key_id, service_account_id, private_key = _extract_sa_credentials(
                None, override_key=service_account_key, override_sa_id=service_account_id_manual
            )
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Создаем JWT токен
        now = datetime.now(timezone.utc)
        iat = int(now.timestamp())
        exp = int((now + timedelta(hours=1)).timestamp())
        
        payload = {
            'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            'iss': service_account_id,
            'iat': iat,
            'exp': exp
        }
        
        # Подписываем JWT приватным ключом
        jwt_headers = {'typ': 'JWT'}
        if key_id:
            jwt_headers['kid'] = key_id
        jwt_token = encode(
            payload,
            private_key,
            algorithm='PS256',
            headers=jwt_headers
        )
        
        # Обмениваем JWT на IAM токен
        iam_response = requests.post(
            'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            json={'jwt': jwt_token},
            timeout=30
        )
        
        if iam_response.status_code != 200:
            return jsonify({
                'error': f'Ошибка получения IAM токена: {iam_response.status_code}',
                'details': iam_response.text
            }), 400
        
        iam_data = iam_response.json()
        iam_token = iam_data.get('iamToken')
        expires_at = datetime.fromisoformat(iam_data.get('expiresAt').replace('Z', '+00:00'))
        expires_in = int((expires_at - datetime.now(timezone.utc)).total_seconds())
        
        return jsonify({
            'success': True,
            'message': 'IAM-токен успешно получен',
            'iamToken': iam_token,
            'expiresIn': expires_in,
            'expiresAt': expires_at.isoformat(),
            'folderId': folder_id
        })
    except ImportError as e:
        return jsonify({
            'error': f'Отсутствует необходимая библиотека: {str(e)}. Установите: pip install PyJWT',
            'details': 'Для работы с IAM токенами требуется библиотека PyJWT'
        }), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
