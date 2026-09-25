"""
API endpoints для настроек Яндекс Облака (SpeechKit + Object Storage, YandexGPT)
и списка движков распознавания/разбора (/api/engines) для переключателя в интерфейсе.

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


def _filled(value):
    return bool(value and str(value).strip())


def missing_for(service, settings):
    """What is not filled in for a cloud service: speechkit needs the key,
    folder and Object Storage (files go through a bucket); yandexgpt — key and folder."""
    need = [('api_key', 'API-ключ'), ('folder_id', 'Folder ID')]
    if service == 'speechkit':
        need += [('bucket_name', 'Имя бакета'), ('access_key_id', 'Access Key ID'),
                 ('secret_access_key', 'Secret Access Key')]
    return [label for field, label in need if not _filled(getattr(settings, field, None))]


def _gigaam_status():
    import requests
    import gigaam_client
    try:
        requests.get(f'{gigaam_client.base_url()}/health', timeout=2).raise_for_status()
        return True, f'Локальный сервис GigaAM ({gigaam_client.model_name()})'
    except Exception:
        return False, 'Сервис GigaAM не отвечает: docker compose up -d gigaam'


@yandex_cloud_bp.route('/engines', methods=['GET'])
def engines():
    """Что можно выбрать в интерфейсе: распознавание (gigaam / speechkit) и разбор
    заказа (rules / llm), готово ли каждое и что выбрано по умолчанию на сервере."""
    import os
    try:
        settings = YandexCloudSettingsRepository.get_settings()
    except Exception as e:
        logger.warning(f"[YC] Настройки недоступны: {e}")
        settings = None
    gigaam_ready, gigaam_detail = _gigaam_status()
    speechkit_missing = missing_for('speechkit', settings)
    llm_missing = missing_for('yandexgpt', settings)
    stt_default = (os.environ.get('STT_ENGINE') or 'speechkit').lower()
    parser_default = (os.environ.get('ORDER_PARSER') or 'rules').lower()
    return jsonify({
        'stt': {
            'default': stt_default if stt_default in ('gigaam', 'speechkit') else 'speechkit',
            'options': [
                {'id': 'gigaam', 'ready': gigaam_ready, 'detail': gigaam_detail, 'missing': []},
                {'id': 'speechkit', 'ready': not speechkit_missing, 'missing': speechkit_missing,
                 'detail': 'Яндекс SpeechKit через Object Storage'},
            ],
        },
        'parser': {
            'default': parser_default if parser_default in ('rules', 'llm') else 'rules',
            'options': [
                {'id': 'rules', 'ready': True, 'missing': [], 'detail': 'По справочнику филиала, без облака'},
                {'id': 'llm', 'ready': not llm_missing, 'missing': llm_missing,
                 'detail': f'YandexGPT ({(settings.yandex_model if settings else None) or "yandexgpt"})'},
            ],
        },
    })


def _test_yandexgpt(settings):
    """One short request to YandexGPT with the saved key: checks the key, folder,
    model and the ai.languageModels.user role."""
    import requests
    model = settings.yandex_model or 'yandexgpt'
    response = requests.post(
        'https://ai.api.cloud.yandex.net/v1/chat/completions',
        headers={'Authorization': f'Api-Key {settings.api_key}', 'x-folder-id': settings.folder_id},
        json={'model': f'gpt://{settings.folder_id}/{model}', 'max_tokens': 5, 'temperature': 0,
              'messages': [{'role': 'user', 'content': 'Ответь одним словом: готов'}]},
        timeout=30,
    )
    if response.status_code != 200:
        detail = response.text[:300]
        hint = ' Проверьте роль ai.languageModels.user у сервисного аккаунта.' if response.status_code in (401, 403) else ''
        return jsonify({'success': False, 'service': 'yandexgpt',
                        'error': f'YandexGPT ответил {response.status_code}: {detail}.{hint}'}), 400
    return jsonify({'success': True, 'service': 'yandexgpt',
                    'message': f'YandexGPT отвечает (модель {model})'})


@yandex_cloud_bp.route('/yandex-cloud/test-connection', methods=['POST'])
def test_connection():
    """
    Проверить настройки одного сервиса ({"service": "speechkit" | "yandexgpt"}):
    speechkit — загружаем тестовый объект в бакет через S3-ключи (без бакета
    SpeechKit файлы не принимает); yandexgpt — короткий запрос к модели.
    """
    try:
        service = ((request.json if request.is_json else None) or {}).get('service') or 'speechkit'
        settings = YandexCloudSettingsRepository.get_settings()
        if not settings:
            return jsonify({'success': False, 'error': 'Настройки не найдены. Сначала сохраните настройки.'}), 404

        missing = missing_for(service, settings)
        if missing:
            return jsonify({'success': False, 'service': service,
                            'error': 'Не заполнено: ' + ', '.join(missing)}), 400
        if service == 'yandexgpt':
            return _test_yandexgpt(settings)

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
