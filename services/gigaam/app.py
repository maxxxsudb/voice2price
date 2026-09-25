"""Unauthenticated asynchronous HTTP API for one local GigaAM worker."""
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import redis
from flask import Flask, jsonify, request

import transcriber

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('gigaam-service')

REDIS_URL = os.environ.get('GIGAAM_REDIS_URL', 'redis://redis:6379/1')
DATA_DIR = Path(os.environ.get('GIGAAM_DATA_DIR', '/data/jobs'))
RESULT_TTL = int(os.environ.get('GIGAAM_RESULT_TTL_SEC', '86400'))
MAX_UPLOAD = int(os.environ.get('GIGAAM_MAX_UPLOAD_MB', '100')) * 1024 * 1024
QUEUE = 'gigaam:queue'


def now():
    return datetime.now(timezone.utc).isoformat()


def operation_key(operation_id):
    return f'gigaam:operation:{operation_id}'


def read_operation(client, operation_id):
    raw = client.get(operation_key(operation_id))
    return json.loads(raw) if raw else None


def write_operation(client, operation, ttl=None):
    key = operation_key(operation['id'])
    client.set(key, json.dumps(operation, ensure_ascii=False))
    if ttl:
        client.expire(key, ttl)


def recover_operations(client):
    """Requeue jobs lost between BLPOP and completion after a service restart."""
    queued = set(client.lrange(QUEUE, 0, -1))
    for key in client.scan_iter(match='gigaam:operation:*'):
        operation = read_operation(client, key.rsplit(':', 1)[-1])
        if not operation or operation.get('done') or operation['id'] in queued:
            continue
        path = Path(operation.get('input_path', ''))
        if path.is_file():
            operation.update(status='queued', recovered_at=now())
            write_operation(client, operation)
            client.rpush(QUEUE, operation['id'])
        else:
            operation.update(done=True, status='error', finished_at=now(),
                             error={'message': 'input file was lost before processing'})
            write_operation(client, operation, RESULT_TTL)


def run_worker(client, stop_event):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    while not stop_event.is_set():
        try:
            recover_operations(client)
            break
        except redis.RedisError:
            logger.exception('redis unavailable during recovery')
            time.sleep(1)
    if os.environ.get('GIGAAM_PRELOAD', '1').lower() not in ('0', 'false', 'no'):
        try:
            transcriber.load_model()
            logger.info('model %s loaded', transcriber.model_name())
        except Exception:
            logger.exception('model preload failed; queued jobs will retry')
    while not stop_event.is_set():
        try:
            queued = client.blpop(QUEUE, timeout=1)
        except redis.RedisError:
            logger.exception('redis queue unavailable')
            time.sleep(1)
            continue
        if not queued:
            continue
        operation_id = queued[1]
        operation = read_operation(client, operation_id)
        if not operation or operation.get('done'):
            continue
        path = Path(operation['input_path'])
        operation.update(status='processing', started_at=now())
        write_operation(client, operation)
        try:
            text, segments = transcriber.transcribe(path)
            operation.update(done=True, status='done', finished_at=now(),
                             response={'text': text, 'segments': segments,
                                       'model': transcriber.model_name()})
        except Exception as exc:
            logger.exception('operation %s failed', operation_id)
            operation.update(done=True, status='error', finished_at=now(),
                             error={'message': str(exc)})
        finally:
            path.unlink(missing_ok=True)
        write_operation(client, operation, RESULT_TTL)


def create_app(redis_client=None, start_worker=True):
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD
    client = redis_client or redis.Redis.from_url(REDIS_URL, decode_responses=True)
    stop_event = threading.Event()
    if start_worker:
        threading.Thread(target=run_worker, args=(client, stop_event), daemon=True,
                         name='gigaam-worker').start()

    @app.get('/health')
    def health():
        try:
            client.ping()
            queue_size = client.llen(QUEUE)
        except Exception as exc:
            return jsonify(status='error', error=str(exc)), 503
        return jsonify(status='ok', model=transcriber.model_name(),
                       model_loaded=transcriber.model_loaded(), queue_size=queue_size)

    @app.post('/v1/transcriptions')
    def create_transcription():
        upload = request.files.get('file')
        if not upload or not upload.filename:
            return jsonify(error='multipart field "file" is required'), 400
        operation_id = uuid.uuid4().hex
        suffix = Path(upload.filename).suffix.lower()[:10] or '.audio'
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = DATA_DIR / f'{operation_id}{suffix}'
        upload.save(path)
        operation = {'id': operation_id, 'done': False, 'status': 'queued',
                     'created_at': now(), 'input_path': str(path),
                     'filename': Path(upload.filename).name}
        write_operation(client, operation)
        client.rpush(QUEUE, operation_id)
        public = {key: value for key, value in operation.items() if key != 'input_path'}
        return jsonify(public), 202

    @app.get('/v1/operations/<operation_id>')
    def get_operation(operation_id):
        operation = read_operation(client, operation_id)
        if not operation:
            return jsonify(error='operation not found'), 404
        return jsonify({key: value for key, value in operation.items() if key != 'input_path'})

    return app


app = create_app(start_worker=os.environ.get('GIGAAM_START_WORKER', '1').lower()
                 not in ('0', 'false', 'no'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5001')),
            threaded=True, use_reloader=False)
