import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import gigaam_client


class GigaamClientTest(unittest.TestCase):
    @patch('gigaam_client.requests.post')
    def test_submit_uploads_file(self, post):
        response = Mock()
        response.json.return_value = {'id': 'operation-1'}
        post.return_value = response
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'order.mp3'
            path.write_bytes(b'audio')
            self.assertEqual(gigaam_client.submit(path), 'operation-1')
        response.raise_for_status.assert_called_once()

    @patch('gigaam_client.get_operation')
    def test_wait_returns_response(self, get_operation):
        get_operation.side_effect = [
            {'id': 'operation-1', 'done': False, 'status': 'processing'},
            {'id': 'operation-1', 'done': True, 'status': 'done',
             'response': {'text': 'бочок индейки два', 'segments': []}},
        ]
        with patch('gigaam_client.time.sleep'):
            result = gigaam_client.wait('operation-1', timeout=1, poll_interval=0.01)
        self.assertEqual(result['text'], 'бочок индейки два')

    @patch('gigaam_client.get_operation')
    def test_wait_raises_service_error(self, get_operation):
        get_operation.return_value = {'done': True, 'status': 'error',
                                      'error': {'message': 'bad audio'}}
        with self.assertRaisesRegex(RuntimeError, 'bad audio'):
            gigaam_client.wait('operation-1')


if __name__ == '__main__':
    unittest.main()
