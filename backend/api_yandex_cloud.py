#!/usr/bin/env python3
"""
API для управления настройками Яндекс Облака.
Хранение JSON-ключей сервисных аккаунтов, IAM токенов и настроек Object Storage.
"""

import json
import time
import jwt
import requests
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session

from models_db import YandexCloudSettings
from database import get_db_session
from repositories import YandexCloudSettingsRepository

yandex_cloud_bp = Blueprint('yandex_cloud', __name__, url_prefix='/yandex-cloud')


@yandex_cloud_bp.route('/settings', methods=['GET'])
def get_settings():
    """Получить текущие настройки Яндекс Облака"""
    try:
        settings = YandexCloudSettingsRepository.get_settings()
        if not settings:
            return jsonify({'message': 'Настройки не найдены'}), 404
        
        # Не возвращаем чувствительные данные
        return jsonify({
            'folder_id': settings.folder_id,
            'bucket_name': settings.bucket_name,
            'endpoint': settings.endpoint,
            'access_key_id': settings.access_key_id,
            'has_service_account_key': bool(settings.service_account_key),
            'has_secret_access_key': bool(settings.secret_access_key),
            'iam_token_valid': settings.is_iam_token_valid() if settings.iam_token else False,
            'updated_at': settings.updated_at.isoformat() if settings.updated_at else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@yandex_cloud_bp.route('/settings', methods=['POST'])
def save_settings():
    """Сохранить настройки Яндекс Облака"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON данные требуются'}), 400
        
        # Проверяем обязательные поля
        required_fields = ['service_account_key']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Поле {field} обязательно'}), 400
        
        # Валидируем JSON ключ сервисного аккаунта
        try:
            sa_key = json.loads(data['service_account_key'])
            if 'private_key' not in sa_key or 'key_id' not in sa_key:
                return jsonify({'error': 'Некорректный формат JSON ключа сервисного аккаунта'}), 400
        except json.JSONDecodeError:
            return jsonify({'error': 'JSON ключ сервисного аккаунта имеет неверный формат'}), 400
        
        # Сохраняем настройки
        settings_data = {
            'service_account_key': data['service_account_key'],
            'folder_id': data.get('folder_id', ''),
            'bucket_name': data.get('bucket_name', ''),
            'endpoint': data.get('endpoint', 'https://storage.yandexcloud.net'),
            'access_key_id': data.get('access_key_id', ''),
            'secret_access_key': data.get('secret_access_key', '')
        }
        
        YandexCloudSettingsRepository.create_or_update(settings_data)
        
        return jsonify({'message': 'Настройки успешно сохранены'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@yandex_cloud_bp.route('/settings', methods=['DELETE'])
def delete_settings():
    """Удалить настройки Яндекс Облака"""
    try:
        YandexCloudSettingsRepository.delete_settings()
        return jsonify({'message': 'Настройки удалены'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@yandex_cloud_bp.route('/iam-token', methods=['POST'])
def generate_iam_token():
    """Сгенерировать новый IAM токен из JSON ключа сервисного аккаунта"""
    try:
        settings = YandexCloudSettingsRepository.get_settings()
        if not settings:
            return jsonify({'error': 'Настройки не найдены. Сначала сохраните JSON ключ сервисного аккаунта.'}), 404
        
        if not settings.service_account_key:
            return jsonify({'error': 'JSON ключ сервисного аккаунта не настроен'}), 400
        
        sa_key = json.loads(settings.service_account_key)
        
        # Генерируем JWT токен
        now = int(time.time())
        payload = {
            'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            'iss': sa_key['id'],
            'iat': now,
            'exp': now + 3600  # 1 час
        }
        
        private_key = sa_key['private_key']
        jwt_token = jwt.encode(payload, private_key, algorithm='PS256', headers={'kid': sa_key['key_id']})
        
        # Обмениваем JWT на IAM токен
        response = requests.post(
            'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            headers={'Authorization': f'Bearer {jwt_token}'},
            timeout=30
        )
        
        if response.status_code != 200:
            return jsonify({'error': f'Ошибка получения IAM токена: {response.text}'}), 500
        
        iam_data = response.json()
        iam_token = iam_data.get('iamToken')
        
        if not iam_token:
            return jsonify({'error': 'IAM токен не получен в ответе'}), 500
        
        # Вычисляем время истечения (токен действителен 1 час)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Сохраняем токен в БД
        YandexCloudSettingsRepository.update_iam_token(iam_token, expires_at)
        
        return jsonify({
            'iam_token': iam_token,
            'expires_at': expires_at.isoformat()
        }), 200
    
    except jwt.exceptions.InvalidKeyError as e:
        return jsonify({'error': f'Неверный формат приватного ключа: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@yandex_cloud_bp.route('/iam-token', methods=['GET'])
def get_iam_token():
    """Получить IAM токен (с автообновлением при истечении)"""
    try:
        settings = YandexCloudSettingsRepository.get_settings()
        if not settings:
            return jsonify({'error': 'Настройки не найдены'}), 404
        
        # Если токен есть и он валиден - возвращаем его
        if settings.iam_token and settings.is_iam_token_valid():
            return jsonify({'iam_token': settings.iam_token, 'cached': True})
        
        # Иначе генерируем новый
        if not settings.service_account_key:
            return jsonify({'error': 'JSON ключ сервисного аккаунта не настроен'}), 400
        
        sa_key = json.loads(settings.service_account_key)
        
        # Генерируем JWT токен
        now = int(time.time())
        payload = {
            'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            'iss': sa_key['id'],
            'iat': now,
            'exp': now + 3600
        }
        
        private_key = sa_key['private_key']
        jwt_token = jwt.encode(payload, private_key, algorithm='PS256', headers={'kid': sa_key['key_id']})
        
        # Обмениваем JWT на IAM токен
        response = requests.post(
            'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            headers={'Authorization': f'Bearer {jwt_token}'},
            timeout=30
        )
        
        if response.status_code != 200:
            return jsonify({'error': f'Ошибка получения IAM токена: {response.text}'}), 500
        
        iam_data = response.json()
        iam_token = iam_data.get('iamToken')
        
        if not iam_token:
            return jsonify({'error': 'IAM токен не получен'}), 500
        
        expires_at = datetime.utcnow() + timedelta(hours=1)
        YandexCloudSettingsRepository.update_iam_token(iam_token, expires_at)
        
        return jsonify({'iam_token': iam_token, 'cached': False}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@yandex_cloud_bp.route('/test-connection', methods=['POST'])
def test_connection():
    """Проверить подключение к Яндекс Облаку"""
    try:
        settings = YandexCloudSettingsRepository.get_settings()
        if not settings:
            return jsonify({'error': 'Настройки не найдены'}), 404
        
        result = {
            'service_account': False,
            'iam_token': False,
            'object_storage': False
        }
        
        # Проверяем наличие JSON ключа
        if settings.service_account_key:
            try:
                sa_key = json.loads(settings.service_account_key)
                if 'private_key' in sa_key and 'id' in sa_key:
                    result['service_account'] = True
            except:
                pass
        
        # Проверяем IAM токен
        if settings.iam_token and settings.is_iam_token_valid():
            result['iam_token'] = True
        
        # Проверяем Object Storage (если настроен)
        if settings.access_key_id and settings.secret_access_key and settings.bucket_name:
            import boto3
            from botocore.exceptions import ClientError
            
            s3 = boto3.client(
                's3',
                endpoint_url=settings.endpoint,
                aws_access_key_id=settings.access_key_id,
                aws_secret_access_key=settings.secret_access_key
            )
            
            try:
                s3.head_bucket(Bucket=settings.bucket_name)
                result['object_storage'] = True
            except ClientError as e:
                result['object_storage_error'] = str(e)
        
        all_ok = result['service_account'] and result['iam_token']
        
        return jsonify({
            'success': all_ok,
            'details': result,
            'message': 'Подключение успешно' if all_ok else 'Часть настроек отсутствует'
        }), 200 if all_ok else 207
    
    except ImportError:
        return jsonify({
            'success': True,
            'details': {'service_account': True, 'iam_token': True, 'object_storage': 'not_configured'},
            'message': 'boto3 не установлен, проверка Object Storage пропущена'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
