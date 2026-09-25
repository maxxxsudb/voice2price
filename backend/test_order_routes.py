"""HTTP contract checks; cloud calls and repositories are mocked."""
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock

from server import app

# A branch with default parsing options
BRANCH = SimpleNamespace(get_order_settings=lambda: None)
from models_db import YandexCloudSettings


class OrderRouteTests(unittest.TestCase):
    def test_mp3_to_catalog_order(self):
        settings = SimpleNamespace(api_key='test-key', folder_id='test-folder',
                                   order_prompt='', yandex_model='yandexgpt')
        product = SimpleNamespace(id='n1', name='Шприц 5 мл', article='A1',
                                  code=None, storage_unit='шт', report_unit='шт')
        response = Mock()
        response.json.return_value = {'choices': [{'finish_reason': 'stop', 'message': {
            'content': json.dumps([{'name': 'шприц', 'nomenclature_id': 'n1',
                                   'quantity': 10, 'unit': 'шт', 'needs_review': False}])}}]}
        with patch('server._get_yc_settings_or_none', return_value=settings), \
             patch('server.analyze_audio', return_value={}), \
             patch('server.recognize_speechkit_v2', return_value=('шприц 5 мл 10 штук', [])), \
             patch('repositories.EmployeeRepository.get_by_id', return_value=BRANCH), \
             patch('repositories.ClientRepository.get_by_employee', return_value=[]), \
             patch('repositories.NomenclatureRepository.get_by_employee', return_value=[product]) as catalog, \
             patch('repositories.VoiceDictionaryRepository.get_data', return_value=[]), \
             patch('requests.post', return_value=response):
            result = app.test_client().post('/api/recognize', data={
                'file': (io.BytesIO(b'test-audio'), 'order.mp3'),
                'employee_id': 'employee-1', 'process_llm': 'true',
            })
        self.assertEqual(result.status_code, 200)
        catalog.assert_called_once_with('employee-1')
        item = result.json['order_items'][0]
        self.assertEqual(item['nomenclature_id'], 'n1')
        self.assertEqual(item['quantity'], 10)
        self.assertFalse(item['needs_review'])

    def test_cloud_failure_preserves_transcript(self):
        settings = SimpleNamespace(api_key='test', folder_id='folder', order_prompt='', yandex_model='yandexgpt')
        with patch('server._get_yc_settings_or_none', return_value=settings), \
             patch('server.analyze_audio', return_value={}), \
             patch('server.recognize_speechkit_v2', return_value=('заказ', [])), \
             patch('server.process_text_with_yandexgpt', side_effect=ValueError('invalid response')):
            result = app.test_client().post('/api/recognize', data={
                'file': (io.BytesIO(b'test'), 'order.mp3'), 'process_llm': 'true',
            })
        self.assertEqual(result.json['text'], 'заказ')
        self.assertIsNone(result.json['order_items'])
        self.assertEqual(result.json['llm_error'], 'invalid response')

    def test_settings_flags_and_empty_secret_preservation(self):
        settings = YandexCloudSettings(api_key='saved-api-secret', secret_access_key='saved-s3-secret')
        public = settings.to_dict()
        self.assertTrue(public['has_api_key'])
        self.assertTrue(public['has_secret_access_key'])
        self.assertNotIn('saved-api-secret', json.dumps(public))
        self.assertNotIn('saved-s3-secret', json.dumps(public))
        with patch('repositories.YandexCloudSettingsRepository.get_settings', return_value=settings), \
             patch('repositories.YandexCloudSettingsRepository.create_or_update', return_value=settings) as save:
            response = app.test_client().post('/api/yandex-cloud/settings', json={
                'apiKey': '', 'secretAccessKey': '', 'orderPrompt': 'updated prompt',
            })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(save.call_args.args[0], {'order_prompt': 'updated prompt'})
        settings.api_key = ' '
        self.assertFalse(settings.to_dict()['has_api_key'])


if __name__ == '__main__':
    unittest.main()
