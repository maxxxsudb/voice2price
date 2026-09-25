"""Route checks for local recognition and for «no silent YandexGPT»; cloud is mocked to fail."""
import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from server import app

PRODUCTS = [SimpleNamespace(id='b', name='Бочок индейки к/в', article=None, code=None,
                            storage_unit='кг', report_unit='кг', nomenclature_type='Товар')]


class LocalRecognitionRouteTests(unittest.TestCase):
    def post(self, **form):
        data = {'file': (io.BytesIO(b'audio'), 'order.mp3'), **form}
        return app.test_client().post('/api/recognize', data=data)

    def test_gigaam_needs_no_cloud(self):
        with patch('server.analyze_audio', return_value={}), \
             patch('gigaam_client.transcribe', return_value=('бочок индейки кило двести', [{'text': 'бочок индейки кило двести'}])), \
             patch('server._get_yc_settings_or_none', side_effect=AssertionError('no cloud settings needed')), \
             patch('server.recognize_speechkit_v2', side_effect=AssertionError('no SpeechKit')), \
             patch('requests.post', side_effect=AssertionError('no network')), \
             patch('repositories.EmployeeRepository.get_by_id', return_value=object()), \
             patch('repositories.NomenclatureRepository.get_by_employee', return_value=PRODUCTS), \
             patch('repositories.VoiceDictionaryRepository.get_data', return_value=[]):
            result = self.post(engine='gigaam', employee_id='e', process_llm='true')
        self.assertEqual(result.status_code, 200, result.json)
        self.assertEqual(result.json['engine'], 'gigaam')
        item = result.json['order_items'][0]
        self.assertEqual((item['nomenclature_id'], item['quantity'], item['needs_review']), ('b', 1.2, False))

    def test_without_employee_no_yandexgpt_call(self):
        with patch('server.analyze_audio', return_value={}), \
             patch('gigaam_client.transcribe', return_value=('бочок индейки два', [])), \
             patch('requests.post', side_effect=AssertionError('YandexGPT must not be called')):
            result = self.post(engine='gigaam', process_llm='true')
        self.assertEqual(result.status_code, 200)
        self.assertIsNone(result.json['order_items'])
        self.assertIn('Выберите сотрудника', result.json['llm_error'])

    def test_process_order_without_employee(self):
        with patch('requests.post', side_effect=AssertionError('YandexGPT must not be called')):
            result = app.test_client().post('/api/process-order', json={'text': 'бочок индейки два'})
        self.assertEqual(result.status_code, 500)
        self.assertIn('Выберите сотрудника', result.json['error'])


if __name__ == '__main__':
    unittest.main()
