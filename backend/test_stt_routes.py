"""Route checks for local recognition and for «no silent YandexGPT»; cloud is mocked to fail."""
import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from server import app

# A branch with default parsing options
BRANCH = SimpleNamespace(get_order_settings=lambda: None)

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
             patch('repositories.EmployeeRepository.get_by_id', return_value=BRANCH), \
             patch('repositories.ClientRepository.get_by_employee', return_value=[]), \
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
        self.assertIn('Выберите филиал', result.json['llm_error'])

    def test_process_order_without_employee(self):
        with patch('requests.post', side_effect=AssertionError('YandexGPT must not be called')):
            result = app.test_client().post('/api/process-order', json={'text': 'бочок индейки два'})
        self.assertEqual(result.status_code, 500)
        self.assertIn('Выберите филиал', result.json['error'])


CLIENTS = [SimpleNamespace(id='c1', name='Нурыев Р.Н. ИП', code='012', public_name='ИП Нурыев Ринат Наилевич')]


def branch_patches(clients=CLIENTS):
    return [patch('repositories.EmployeeRepository.get_by_id', return_value=BRANCH),
            patch('repositories.ClientRepository.get_by_employee', return_value=clients),
            patch('repositories.NomenclatureRepository.get_by_employee', return_value=PRODUCTS),
            patch('repositories.VoiceDictionaryRepository.get_data', return_value=[])]


class ClientApiTests(unittest.TestCase):
    def setUp(self):
        for p in branch_patches():
            p.start()
            self.addCleanup(p.stop)

    def test_recognize_returns_client_without_order_parsing(self):
        with patch('server.analyze_audio', return_value={}), \
             patch('gigaam_client.transcribe', return_value=('нурыеву бочок индейки два', [])):
            result = app.test_client().post('/api/recognize', data={
                'file': (io.BytesIO(b'audio'), 'order.mp3'), 'engine': 'gigaam', 'employee_id': 'e'})
        self.assertEqual(result.status_code, 200, result.json)
        self.assertIsNone(result.json['order_items'])
        self.assertEqual((result.json['client']['client_id'], result.json['client']['needs_review']), ('c1', False))

    def test_detect_client_route(self):
        result = app.test_client().post('/api/detect-client', json={'employee_id': 'e', 'text': 'нурыев бочок два'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['client']['client_id'], 'c1')
        self.assertEqual(result.json['client']['confidence'], .85)
        result = app.test_client().post('/api/detect-client', json={'text': 'нурыев'})
        self.assertEqual(result.status_code, 400)

    def test_parser_is_chosen_per_request(self):
        rules = app.test_client().post('/api/process-order', json={
            'text': 'нурыев бочок индейки два', 'employee_id': 'e', 'parser': 'rules'})
        self.assertEqual((rules.json['parser'], rules.json['client']['client_id']), ('rules', 'c1'))
        self.assertEqual(rules.json['order_items'][0]['nomenclature_id'], 'b')
        with patch('server._get_yc_settings_or_none', return_value=None), \
             patch('requests.post', side_effect=AssertionError('no key — no call')):
            llm = app.test_client().post('/api/process-order', json={
                'text': 'нурыев бочок индейки два', 'employee_id': 'e', 'parser': 'llm'})
        self.assertEqual(llm.status_code, 500)
        self.assertIn('API-ключ', llm.json['error'])


if __name__ == '__main__':
    unittest.main()
