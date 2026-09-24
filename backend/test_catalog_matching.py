import unittest
from catalog_matching import CatalogIndex, guarded_selection, is_metadata


class MatchingTests(unittest.TestCase):
    catalog = [
        {'id': 'a', 'name': 'Сервелат Венский', 'storage_unit': 'кг'},
        {'id': 'b', 'name': 'Сервелат Венский газ', 'storage_unit': 'кг'},
        {'id': 'c', 'name': 'Сосиски из индейки Люкс', 'storage_unit': 'кг'},
    ]

    def test_valid_number_with_wrong_name_is_not_silently_renamed(self):
        result = guarded_selection({'spoken_name': 'сосиски', 'quantity': 1}, self.catalog,
            {'choice': 1, 'name': self.catalog[2]['name'], 'needs_review': False})
        self.assertIsNone(result['nomenclature_id'])
        self.assertTrue(result['needs_review'])

    def test_unspoken_units_use_catalog_not_model_guess(self):
        item = {'spoken_name': 'сосиски люкс', 'quantity': 2,
                'source_text': 'сосиски люкс два', 'explicit_unit': 'шт'}
        decision = {'choice': 3, 'name': self.catalog[2]['name'], 'needs_review': False}
        result = guarded_selection(item, self.catalog, decision)
        self.assertEqual(result['unit'], 'кг')
        self.assertEqual(result['unit_source'], 'catalog')
        item['source_text'] = 'сосиски люкс две штуки'
        self.assertEqual(guarded_selection(item, self.catalog, decision)['unit'], 'шт')

    def test_ambiguous_packaging_requires_selection(self):
        result = guarded_selection({'spoken_name': 'сервелат венский', 'quantity': 5}, self.catalog,
            {'choice': 1, 'name': self.catalog[0]['name'], 'needs_review': False})
        self.assertIsNone(result['nomenclature_id'])
        self.assertTrue(result['needs_review'])

    def test_metadata_filter_keeps_product_with_unknown_quantity(self):
        self.assertTrue(is_metadata({'source_text': 'городская машина'}))
        self.assertTrue(is_metadata({'source_text': 'нулевой процентный прайс'}))
        self.assertFalse(is_metadata({'source_text': 'сосиски люкс', 'quantity': None}))

    def test_retrieval_keeps_competing_packaging(self):
        self.assertEqual(set(CatalogIndex(self.catalog).rank('сервелат венский', 2)), {0, 1})
