"""
API endpoints для работы с настройками Яндекс Облака (Object Storage, IAM, сервисный аккаунт).
Все настройки хранятся в базе данных.
"""

import json
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from repositories import YandexCloudSettingsRepository

yandex_cloud_bp = Blueprint('yandex_cloud', __name__)


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
    Сохранить настройки Яндекс Облака.
    
    Принимает JSON:
    {
        "service_account_key": "{...}",  // JSON-ключ сервисного аккаунта (обязательно для IAM токена)
        "folder_id": "b1g...",           // Folder ID для SpeechKit
        "bucket_name": "my-bucket",      // Имя бакета Object Storage
        "endpoint": "https://storage.yandexcloud.net",
        "access_key_id": "YCAB...",      // Access Key для Object Storage
        "secret_access_key": "..."       // Secret Key для Object Storage
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Требуется JSON тело запроса'}), 400
        
        # Валидация service_account_key если предоставлен
        service_account_key = data.get('service_account_key')
        if service_account_key:
            try:
                # Проверяем что это валидный JSON
                key_data = json.loads(service_account_key)
                if not isinstance(key_data, dict):
                    return jsonify({'error': 'service_account_key должен быть JSON объектом'}), 400
                # Проверяем наличие обязательных полей
                required_fields = ['id', 'subject_token_audience']
                for field in required_fields:
                    if field not in key_data:
                        return jsonify({'error': f'В JSON-ключе отсутствует поле: {field}'}), 400
            except json.JSONDecodeError as e:
                return jsonify({'error': f'Невалидный JSON в service_account_key: {str(e)}'}), 400
        
        # Сохраняем настройки
        settings = YandexCloudSettingsRepository.create_or_update(data)
        
        return jsonify({
            'message': 'Настройки сохранены',
            'settings': settings.to_dict()
        }), 201
    except Exception as e:
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
        
        if not settings or not settings.service_account_key:
            return jsonify({
                'error': 'JSON-ключ сервисного аккаунта не настроен. Пожалуйста, сохраните настройки.'
            }), 400
        
        # Парсим JSON-ключ
        key_data = json.loads(settings.service_account_key)
        
        # Извлекаем необходимые данные из ключа
        subject_token_audience = key_data.get('subject_token_audience', 'urn:ietf:params:oauth:token-type:jwt')
        key_id = key_data.get('key_id')
        service_account_id = key_data.get('id')
        
        if not all([key_id, service_account_id]):
            return jsonify({
                'error': 'В JSON-ключе отсутствуют обязательные поля: key_id или id'
            }), 400
        
        # Создаем JWT токен
        now = datetime.now(timezone.utc)
        iat = int(now.timestamp())
        exp = int((now + timedelta(hours=1)).timestamp())
        
        payload = {
            'aud': subject_token_audience,
            'iss': service_account_id,
            'iat': iat,
            'exp': exp
        }
        
        # Подписываем JWT приватным ключом
        private_key = key_data.get('private_key')
        if not private_key:
            return jsonify({'error': 'В JSON-ключе отсутствует private_key'}), 400
        
        jwt_token = encode(
            payload,
            private_key,
            algorithm='PS256',
            headers={'kid': key_id, 'typ': 'JWT'}
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
                'error': 'JSON-ключ сервисного аккаунта не настроен'
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
        
        key_data = json.loads(settings.service_account_key)
        key_id = key_data.get('key_id')
        service_account_id = key_data.get('id')
        subject_token_audience = key_data.get('subject_token_audience', 'urn:ietf:params:oauth:token-type:jwt')
        private_key = key_data.get('private_key')
        
        now = datetime.now(timezone.utc)
        iat = int(now.timestamp())
        exp = int((now + timedelta(hours=1)).timestamp())
        
        payload = {
            'aud': subject_token_audience,
            'iss': service_account_id,
            'iat': iat,
            'exp': exp
        }
        
        jwt_token = encode(
            payload,
            private_key,
            algorithm='PS256',
            headers={'kid': key_id, 'typ': 'JWT'}
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
