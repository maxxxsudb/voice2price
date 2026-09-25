"""SpeechKit and YandexGPT plumbing; the network and Object Storage are mocked."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import server
from server import app

SETTINGS = SimpleNamespace(api_key='key', folder_id='b1gfolder', bucket_name='bucket',
                           access_key_id='id', secret_access_key='secret', yandex_model='yandexgpt-lite')


def reply(status, payload=None):
    return Mock(status_code=status, json=Mock(return_value=payload or {}), text=str(payload), headers={})


class SpeechKitTest(unittest.TestCase):
    def test_failed_polling_stops_at_once(self):
        with patch('requests.post', return_value=reply(200, {'id': 'op1'})), \
             patch('requests.get', return_value=reply(401, {'message': 'Unauthorized'})) as poll, \
             patch('time.sleep', side_effect=AssertionError('must not wait')):
            with self.assertRaisesRegex(RuntimeError, '401'):
                server.recognize_via_storage_uri('https://storage/x', 'key', 'b1gfolder')
        self.assertEqual(poll.call_count, 1)

    def test_uploaded_audio_is_deleted_even_on_error(self):
        prepared = Mock()
        prepared.__enter__ = Mock(return_value=('/tmp/a.pcm', {'source_channels': 1, 'encoding': 'LINEAR16_PCM',
                                                               'sample_rate': 16000}))
        prepared.__exit__ = Mock(return_value=False)
        with patch('audio_preparation.first_channel_pcm', return_value=prepared), \
             patch('server.upload_to_object_storage', return_value='https://storage/x'), \
             patch('server.recognize_via_storage_uri', side_effect=RuntimeError('boom')), \
             patch('server.delete_from_object_storage') as delete:
            with self.assertRaises(RuntimeError):
                server.recognize_speechkit_v2('/tmp/a.mp3', 'a.mp3', 'key', 'b1gfolder', SETTINGS)
        delete.assert_called_once()
        self.assertTrue(delete.call_args.args[0].startswith('audio-uploads/'))


class EnginesTest(unittest.TestCase):
    def test_readiness_of_each_option(self):
        partial = SimpleNamespace(**dict(vars(SETTINGS), bucket_name='', secret_access_key=''))
        with patch('repositories.YandexCloudSettingsRepository.get_settings', return_value=partial), \
             patch('requests.get', side_effect=ConnectionError('down')):
            data = app.test_client().get('/api/engines').json
        stt = {o['id']: o for o in data['stt']['options']}
        parser = {o['id']: o for o in data['parser']['options']}
        self.assertFalse(stt['gigaam']['ready'])
        self.assertEqual(stt['speechkit']['missing'], ['Имя бакета', 'Secret Access Key'])
        self.assertTrue(parser['rules']['ready'])
        self.assertTrue(parser['llm']['ready'])  # YandexGPT needs no bucket
        self.assertIn('yandexgpt-lite', parser['llm']['detail'])

    def test_yandexgpt_check_uses_saved_key(self):
        with patch('repositories.YandexCloudSettingsRepository.get_settings', return_value=SETTINGS), \
             patch('requests.post', return_value=reply(200, {'choices': []})) as call:
            response = app.test_client().post('/api/yandex-cloud/test-connection', json={'service': 'yandexgpt'})
        self.assertTrue(response.json['success'], response.json)
        self.assertEqual(call.call_args.kwargs['headers']['Authorization'], 'Api-Key key')
        self.assertEqual(call.call_args.kwargs['json']['model'], 'gpt://b1gfolder/yandexgpt-lite')

    def test_yandexgpt_check_reports_missing_fields(self):
        empty = SimpleNamespace(**dict(vars(SETTINGS), api_key=''))
        with patch('repositories.YandexCloudSettingsRepository.get_settings', return_value=empty):
            response = app.test_client().post('/api/yandex-cloud/test-connection', json={'service': 'yandexgpt'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('API-ключ', response.json['error'])


if __name__ == '__main__':
    unittest.main()
