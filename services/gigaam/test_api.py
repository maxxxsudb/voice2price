import json
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

os.environ['GIGAAM_START_WORKER'] = '0'
import app as service


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.queue = []

    def ping(self):
        return True

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value

    def expire(self, key, ttl):
        return True

    def rpush(self, key, value):
        self.queue.append(value)

    def llen(self, key):
        return len(self.queue)

    def lrange(self, key, start, end):
        return list(self.queue)

    def scan_iter(self, match=None):
        return iter(self.values)


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.directory = tempfile.TemporaryDirectory()
        self.data_patch = patch.object(service, 'DATA_DIR', Path(self.directory.name))
        self.data_patch.start()
        self.client = service.create_app(self.redis, start_worker=False).test_client()

    def tearDown(self):
        self.data_patch.stop()
        self.directory.cleanup()

    def test_create_and_read_operation(self):
        response = self.client.post('/v1/transcriptions',
                                    data={'file': (BytesIO(b'audio'), 'order.mp3')})
        self.assertEqual(response.status_code, 202)
        operation_id = response.json['id']
        self.assertEqual(response.json['status'], 'queued')
        self.assertNotIn('input_path', response.json)
        stored = json.loads(self.redis.get(service.operation_key(operation_id)))
        self.assertTrue(Path(stored['input_path']).exists())
        result = self.client.get(f'/v1/operations/{operation_id}')
        self.assertEqual(result.json['status'], 'queued')
        self.assertNotIn('input_path', result.json)

    def test_missing_file_and_unknown_operation(self):
        self.assertEqual(self.client.post('/v1/transcriptions').status_code, 400)
        self.assertEqual(self.client.get('/v1/operations/missing').status_code, 404)

    def test_interrupted_operation_is_requeued(self):
        path = Path(self.directory.name) / 'audio.mp3'
        path.write_bytes(b'audio')
        operation = {'id': 'recover-me', 'done': False, 'status': 'processing',
                     'input_path': str(path)}
        service.write_operation(self.redis, operation)
        service.recover_operations(self.redis)
        recovered = service.read_operation(self.redis, 'recover-me')
        self.assertEqual(recovered['status'], 'queued')
        self.assertEqual(self.redis.queue, ['recover-me'])


if __name__ == '__main__':
    unittest.main()
