"""
API endpoints для настроек Яндекс Облака (SpeechKit + Object Storage).

Набор параметров ровно такой, как в рабочей схеме распознавания:
  - API_KEY       — API-ключ сервисного аккаунта SpeechKit (AQVN...)
  - FOLDER_ID     — каталог (b1g...)
  - BUCKET        — имя бакета Object Storage
  - ACCESS_KEY_ID / SECRET_ACCESS_KEY — статические S3-ключи сервисного аккаунта

Никаких IAM-токенов, JSON/PEM-ключей сервисного аккаунта и endpoint'ов —
в этой схеме они не используются.
"""

import logging
from flask import Blueprint, request, jsonify
from repositories import YandexCloudSettingsRepository

yandex_cloud_bp = Blueprint('yandex_cloud', __name__)
logger = logging.getLogger(__name__)

# Поля, которые принимает/хранит API (соответствуют колонкам модели)
FIELDS = ('api_key', 'folder_id', 'bucket_name', 'access_key_id', 'secret_access_key',
          'order_prompt', 'yandex_model')

# camelCase (фронт) -> snake_case (БД)
CAMEL_TO_SNAKE = {
    'apiKey': 'api_key',
    'folderId': 'folder_id',
    'bucketName': 'bucket_name',
    'accessKeyId': 'access_key_id',
    'secretAccessKey': 'secret_access_key',
    'orderPrompt': 'order_prompt',
    'yandexModel': 'yandex_model',
}


def _normalize(data: dict) -> dict:
    normalized = {}
    for src, dst in CAMEL_TO_SNAKE.items():
        if src in data:
            normalized[dst] = data[src]
    for dst in FIELDS:
        if dst in data:
            normalized[dst] = data[dst]
    return normalized


@yandex_cloud_bp.route('/yandex-cloud/settings', methods=['GET'])
def get_settings():
    """Получить текущие настройки Яндекс Облака из БД."""
    try:
        settings = YandexCloudSettingsRepository.get_settings()
        if not settings:
            return jsonify({
                'settings': None,
                'message': 'Настройки не найдены. Пожалуйста, заполните и сохраните настройки.'
            })
        return jsonify({'settings': settings.to_dict()})
    except Exception as e:
        logger.error(f"[YC] Ошибка получения настроек: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@yandex_cloud_bp.route('/yandex-cloud/settings', methods=['POST'])
def save_settings():
    """
    Сохранить настройки Яндекс Облака в БД.

    Принимает JSON (camelCase или snake_case):
    {
        "apiKey": "AQVN...",           // API-ключ сервисного аккаунта SpeechKit
        "folderId": "b1g...",          // Folder ID
        "bucketName": "speech-file",   // Имя бакета Object Storage
        "accessKeyId": "YCAJE...",     // S3 Access Key (IAM -> ключ доступа)
        "secretAccessKey": "YCONF..."  // S3 Secret Key
    }
    Пустые поля не затирают уже сохранённые значения.
    """
    try:
        data = request.json or {}
        normalized = _normalize(data)

        if not any((normalized.get(f) or '').strip() for f in FIELDS):
            return jsonify({'error': 'Пустой запрос: не передано ни одного поля настроек'}), 400

        # Не затираем пустыми строками уже сохранённые секреты
        existing = None
        try:
            existing = YandexCloudSettingsRepository.get_settings()
        except Exception as e:
            logger.warning(f"[YC] Не удалось прочитать существующие настройки: {e}")

        if existing:
            for f in FIELDS:
                if f in normalized and not (normalized[f] or '').strip():
                    normalized.pop(f)

        settings = YandexCloudSettingsRepository.create_or_update(normalized)
        logger.info(f"✅ [YC] Настройки сохранены в БД (id={settings.id}, folder={settings.folder_id}, bucket={settings.bucket_name})")

        return jsonify({
            'message': 'Настройки сохранены в базе данных',
            'settings': settings.to_dict()
        }), 201
    except Exception as e:
        logger.error(f"[YC] Ошибка сохранения настроек: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@yandex_cloud_bp.route('/yandex-cloud/settings', methods=['DELETE'])
def delete_settings():
    """Удалить настройки Яндекс Облака."""
    try:
        success = YandexCloudSettingsRepository.delete_settings()
        if success:
            return jsonify({'message': 'Настройки удалены'})
        return jsonify({'message': 'Настройки не найдены'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@yandex_cloud_bp.route('/yandex-cloud/test-connection', methods=['POST'])
def test_connection():
    """
    Проверить настройки: загружаем тестовый объект в бакет через S3-ключи.
    Это единственная реальная проверка доступности Object Storage + SpeechKit-кредов.
    """
    try:
        settings = YandexCloudSettingsRepository.get_settings()
        if not settings:
            return jsonify({'success': False, 'error': 'Настройки не найдены. Сначала сохраните настройки.'}), 404

        missing = []
        if not settings.api_key: missing.append('API-ключ SpeechKit')
        if not settings.folder_id: missing.append('Folder ID')
        if not settings.bucket_name: missing.append('Имя бакета')
        if not settings.access_key_id: missing.append('Access Key ID')
        if not settings.secret_access_key: missing.append('Secret Access Key')
        if missing:
            return jsonify({'success': False, 'error': 'Не заполнено: ' + ', '.join(missing)}), 400

        from server import upload_to_object_storage
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as tmp:
            tmp.write('audio-analyzer connection test')
            tmp_path = tmp.name
        try:
            from datetime import datetime, timezone
            object_key = f"connection-tests/test-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.txt"
            uri = upload_to_object_storage(tmp_path, object_key, settings)

            # подчищаем тестовый объект
            try:
                import boto3
                s3 = boto3.session.Session().client(
                    service_name='s3',
                    endpoint_url='https://storage.yandexcloud.net',
                    region_name='ru-central1',
                    aws_access_key_id=settings.access_key_id,
                    aws_secret_access_key=settings.secret_access_key,
                )
                s3.delete_object(Bucket=settings.bucket_name, Key=object_key)
            except Exception as del_err:
                logger.warning(f"[YC] Не удалось удалить тестовый объект: {del_err}")

            return jsonify({'success': True, 'message': f'Загрузка в Object Storage успешна: {uri}'})
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except ImportError as e:
        return jsonify({'success': False, 'error': f'Отсутствует библиотека boto3: {e}. Выполните: pip install boto3'}), 500
    except Exception as e:
        logger.error(f"[YC] Ошибка проверки подключения: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Ошибка проверки подключения: {str(e)}'}), 500
