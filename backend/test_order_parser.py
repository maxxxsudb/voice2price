import json
import unittest
from unittest.mock import Mock, patch

from order_parser import extract_order, validate_items


class OrderParserTests(unittest.TestCase):
    catalog = [{'id': 'n1', 'name': 'Шприц 5 мл'}]

    def item(self, **changes):
        return dict(name='шприцы', nomenclature_id='n1', quantity=2,
                    unit='уп', needs_review=False, **changes)

    def test_canonical_name_and_fractional_quantity(self):
        item = self.item()
        item['quantity'] = 2.5
        result = validate_items(json.dumps([item]), self.catalog)[0]
        self.assertEqual(result['name'], 'Шприц 5 мл')
        self.assertEqual(result['quantity'], 2.5)
        self.assertFalse(result['needs_review'])

    def test_bad_quantities_require_review(self):
        for quantity in [None, True, 0, -1, '2', float('nan'), float('inf')]:
            with self.subTest(quantity=quantity):
                item = self.item()
                item['quantity'] = quantity
                result = validate_items(json.dumps([item]), self.catalog)[0]
                self.assertIsNone(result['quantity'])
                self.assertTrue(result['needs_review'])

    def test_unknown_or_other_employee_id_is_not_accepted(self):
        item = self.item()
        item['nomenclature_id'] = 'other-employee-item'
        result = validate_items(json.dumps([item]), self.catalog)[0]
        self.assertIsNone(result['nomenclature_id'])
        self.assertTrue(result['needs_review'])

    def test_ambiguity_is_preserved(self):
        item = self.item()
        item.update(nomenclature_id=None, needs_review=True,
                    review_reason='Несколько размеров')
        result = validate_items(json.dumps([item]), self.catalog)[0]
        self.assertIn('Несколько размеров', result['review_reason'])

    def test_invalid_structure_is_rejected(self):
        for output in ['{}', '[1]', '[{}]', 'null', '[', '[{"name": ""}]']:
            with self.subTest(output=output), self.assertRaises(ValueError):
                validate_items(output, self.catalog)

    def test_fenced_json_and_empty_order(self):
        self.assertEqual(validate_items('```json\n[]\n```', []), [])

    @patch('requests.post')
    def test_api_contract_and_truncated_response(self, post):
        response = Mock()
        post.return_value = response
        response.json.return_value = {'choices': [{'finish_reason': 'stop',
            'message': {'content': json.dumps([self.item()])}}]}
        items = extract_order('шприцы две упаковки', 'key', 'folder', catalog=self.catalog)
        body = post.call_args.kwargs['json']
        self.assertEqual(body['max_tokens'], 4000)
        self.assertIn('content', body['messages'][0])
        self.assertNotIn('completion_options', body)
        self.assertEqual(json.loads(body['messages'][1]['content'])['catalog'], self.catalog)
        self.assertEqual(items[0]['nomenclature_id'], 'n1')
        response.json.return_value['choices'][0]['finish_reason'] = 'length'
        with self.assertRaises(ValueError):
            extract_order('заказ', 'key', 'folder')
        response.raise_for_status.side_effect = RuntimeError('API failed')
        with self.assertRaises(RuntimeError):
            extract_order('заказ', 'key', 'folder')


if __name__ == '__main__':
    unittest.main()
