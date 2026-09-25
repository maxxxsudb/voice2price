"""Branch options: realistic quantities, catalog validation, client, merged messages."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from catalog_validation import validate_catalog
from client_matching import detect_client
from order_merging import parse_messages, recorded_at
from order_pipeline import parse_order
from order_settings import DEFAULTS, clean
from test_order_pipeline import CATALOG, SIMPLE

CLIENTS = [{'id': 'm', 'name': 'ИП Мустафина Лилия', 'public_name': 'Мустафино'},
           {'id': 'g', 'name': 'ООО "Ганеево"'},
           {'id': 'r1', 'name': 'Магазин Ромашка'},
           {'id': 'r2', 'name': 'Ромашка-2'}]


class SettingsTest(unittest.TestCase):
    def test_unknown_and_invalid_values_fall_back(self):
        settings = clean({'plausibility': 'no', 'max_kg': -1, 'hack': 1, 'merge_window_min': 5})
        self.assertEqual(settings['plausibility'], DEFAULTS['plausibility'])
        self.assertIsNone(settings['max_kg'])
        self.assertEqual(settings['merge_window_min'], 5)
        self.assertNotIn('hack', settings)
        self.assertEqual(clean('not json'), DEFAULTS)

    def test_branch_limits_are_off_by_default_and_can_be_cleared(self):
        self.assertEqual((DEFAULTS['max_kg'], DEFAULTS['max_pcs'], DEFAULTS['max_packs']), (None, None, None))
        self.assertEqual(clean({'max_kg': 20})['max_kg'], 20)
        self.assertIsNone(clean({'max_kg': None})['max_kg'])


class PlausibilityTest(unittest.TestCase):
    catalog = [dict(SIMPLE[0], max_quantity=5), SIMPLE[1]]

    def test_no_limit_no_review(self):
        # a big order of a product without a limit is not sent to review
        line = parse_order('колбаса докторская шестьдесят', self.catalog)[0]
        self.assertEqual((line['quantity'], line['needs_review']), (60, False))

    def test_grams_over_product_limit_are_converted(self):
        line = parse_order('сосиски молочные пятьсот', self.catalog)[0]
        self.assertEqual((line['quantity'], line['unit'], line['needs_review']), (0.5, 'кг', False))
        self.assertIn('граммы', line['auto_note'])

    def test_unrealistic_quantity_with_spoken_unit_goes_to_review(self):
        line = parse_order('сосиски молочные пятьсот килограмм', self.catalog)[0]
        self.assertEqual(line['quantity'], 500)
        self.assertTrue(line['needs_review'])
        self.assertIn('Нереалистичное', line['review_reason'])
        line = parse_order('сосиски молочные шесть', self.catalog)[0]  # 6 kg, not grams
        self.assertEqual((line['quantity'], line['needs_review']), (6, True))

    def test_branch_limit_for_products_without_own_limit(self):
        line = parse_order('колбаса докторская триста', self.catalog, settings={'max_kg': 20})[0]
        self.assertEqual((line['quantity'], line['needs_review']), (0.3, False))
        line = parse_order('колбаса докторская шестьдесят', self.catalog, settings={'max_kg': 20})[0]
        self.assertTrue(line['needs_review'])

    def test_product_limit_is_in_its_storage_unit(self):
        catalog = [dict(SIMPLE[0], max_quantity=5)]
        line = parse_order('сосиски молочные десять штук', catalog)[0]
        self.assertNotIn('Нереалистичное', line['review_reason'])

    def test_can_be_turned_off(self):
        line = parse_order('сосиски молочные пятьсот', self.catalog, settings={'plausibility': False})[0]
        self.assertEqual((line['quantity'], line['needs_review']), (500, False))
        line = parse_order('сосиски молочные пятьсот', self.catalog, settings={'grams_over_limit': False})[0]
        self.assertEqual((line['quantity'], line['needs_review']), (500, True))
        self.assertNotIn('auto_note', line)


class SizeInNameTest(unittest.TestCase):
    def test_pack_size_picks_the_product_not_the_quantity(self):
        line = parse_order('зельц говяжий двести пятьдесят', CATALOG)[0]
        self.assertEqual((line['nomenclature_id'], line['quantity'], line['unit']), ('zelc250', None, 'шт'))
        self.assertIn('фасовка', line['review_reason'])
        line = parse_order('зельц говяжий две тысячи пятьсот', CATALOG)[0]
        self.assertEqual((line['nomenclature_id'], line['quantity']), ('zelc2500', None))

    def test_real_quantities_are_kept(self):
        line = parse_order('зельц говяжий весовой два с половиной', CATALOG)[0]
        self.assertEqual((line['nomenclature_id'], line['quantity'], line['needs_review']), ('zelc2500', 2.5, False))
        line = parse_order('бочок индейки двести пятьдесят', CATALOG)[0]  # no size in the name
        self.assertEqual(line['quantity'], 250)

    def test_can_be_turned_off(self):
        line = parse_order('зельц говяжий двести пятьдесят', CATALOG, settings={'size_in_name': False})[0]
        self.assertEqual(line['quantity'], 250)


class CatalogValidationTest(unittest.TestCase):
    def test_problems_are_reported(self):
        rows = CATALOG + [{'id': 'dup', 'name': 'Бочок  индейки К/В', 'article': 'A'},
                          {'id': 'x', 'name': 'Сосиски', 'article': 'a'}]
        dictionary = [{'category': 'nomenclature', 'original': 'Бочок индейки к/в', 'variants': [{'variant': 'бачок'}]},
                      {'category': 'nomenclature', 'original': 'Сосиски', 'variants': [{'variant': 'бачок'}]}]
        report = validate_catalog(rows, dictionary, CLIENTS + [{'id': 'r3', 'name': 'ООО Ромашка-2'}])
        kinds = {i['kind'] for i in report['issues']}
        self.assertTrue({'duplicate_name', 'differs_by_numbers', 'duplicate_article',
                         'ambiguous_variant', 'duplicate_client', 'excluded'} <= kinds, kinds)
        duplicate = next(i for i in report['issues'] if i['kind'] == 'duplicate_name')
        self.assertEqual(duplicate['level'], 'error')
        self.assertEqual({i['id'] for i in duplicate['items']}, {'bochok', 'dup'})
        self.assertEqual(report['counts']['error'], 1)

    def test_clean_catalog(self):
        self.assertEqual(validate_catalog(SIMPLE, settings={'plausibility': False})['issues'], [])

    def test_products_without_limit_are_listed(self):
        catalog = [dict(SIMPLE[0], max_quantity=5), SIMPLE[1]]
        issue = next(i for i in validate_catalog(catalog)['issues'] if i['kind'] == 'no_limit')
        self.assertEqual([i['id'] for i in issue['items']], ['k'])
        kinds = {i['kind'] for i in validate_catalog(catalog, settings={'max_kg': 20})['issues']}
        self.assertNotIn('no_limit', kinds)


class OverlapTest(unittest.TestCase):
    def test_name_contained_in_another_is_reported_with_the_difference(self):
        from catalog_validation import overlapping_products
        catalog = [{'id': 'v', 'name': 'Сервелат "Венский " п/к', 'storage_unit': 'кг'},
                   {'id': 'g', 'name': 'Сервелат "Венский " п/к  газ', 'storage_unit': 'кг'},
                   {'id': 'p', 'name': 'Колбаски " Пикантные " ( 0.100 гр ШТ )', 'storage_unit': 'шт'},
                   {'id': 'q', 'name': 'Колбаски " Пикантные "', 'storage_unit': 'кг'},
                   {'id': 'k', 'name': 'Колбаса докторская', 'storage_unit': 'кг'}]
        rows = {r['product']['id']: [(o['product']['id'], o['say']) for o in r['also']]
                for r in overlapping_products(catalog)}
        self.assertEqual(rows, {'v': [('g', 'газ')], 'q': [('p', 'шт')]})
        issue = next(i for i in validate_catalog(catalog)['issues'] if i['kind'] == 'overlapping_products')
        self.assertEqual(issue['level'], 'warning')
        self.assertIn('уйдёт на ручную проверку', issue['message'])


class ClientTest(unittest.TestCase):
    def test_client_from_message_start(self):
        client = detect_client('мустафино лениногорск бочок индейки кило двести', CLIENTS, CATALOG)
        self.assertEqual((client['client_id'], client['needs_review']), ('m', False))
        client = detect_client('ганеево альметьевск бочок индейки два', CLIENTS, CATALOG)
        self.assertEqual((client['client_id'], client['needs_review']), ('g', False))

    def test_ambiguous_or_missing_client_goes_to_review(self):
        client = detect_client('ромашка бочок индейки два', CLIENTS, CATALOG)
        self.assertTrue(client['needs_review'])
        self.assertEqual({c['id'] for c in client['candidates']}, {'r1', 'r2'})
        self.assertEqual(detect_client('магазин ромашка бочок два', CLIENTS, CATALOG)['client_id'], 'r1')
        missing = detect_client('бочок индейки два', CLIENTS, CATALOG)
        self.assertIsNone(missing['client_id'])
        self.assertTrue(missing['needs_review'])
        self.assertIsNone(detect_client('бочок индейки два', [], CATALOG))

    def test_client_pronunciation_variant(self):
        dictionary = [{'category': 'client', 'original': 'ООО "Ганеево"', 'item_id': 'g',
                       'variants': [{'variant': 'ганеевский магазин'}]}]
        client = detect_client('ганеевский магазин бочок два', CLIENTS[1:2], CATALOG, dictionary)
        self.assertEqual((client['client_id'], client['needs_review']), ('g', False))


class MergeTest(unittest.TestCase):
    def messages(self):
        return [
            {'id': 'a', 'file_name': '2026-08-23 21-37-42.mp3',
             'text': 'мустафино бочок индейки кило двести рулет индейка запеченный'},
            {'id': 'b', 'file_name': '2026-08-23 21-37-54.mp3',
             'text': 'два с половиной килограмма краковская килограмм'},
            {'id': 'c', 'file_name': '2026-08-23 21-38-09.mp3', 'text': 'ганеево бочок индейки два'},
            {'id': 'd', 'file_name': '2026-08-23 23-38-09.mp3', 'text': 'бочок индейки три'},
        ]

    def test_continuation_is_merged_other_client_and_late_message_are_not(self):
        orders = parse_messages(self.messages(), CATALOG, CLIENTS)
        self.assertEqual([o['message_ids'] for o in orders], [['a', 'b'], ['c'], ['d']])
        first = orders[0]
        self.assertEqual(first['client']['client_id'], 'm')
        self.assertIn('количества', first['merge_reasons'][0])
        self.assertEqual([(l['nomenclature_id'], l['quantity']) for l in first['order_items']],
                         [('bochok', 1.2), ('rulet', 2.5), ('krakov', 1)])

    def test_sorted_by_recording_time(self):
        orders = parse_messages(list(reversed(self.messages()[:2])), CATALOG, CLIENTS)
        self.assertEqual(orders[0]['message_ids'], ['a', 'b'])

    def test_merge_can_be_turned_off(self):
        orders = parse_messages(self.messages(), CATALOG, CLIENTS, settings={'merge_messages': False})
        self.assertEqual(len(orders), 4)

    def test_same_client_in_window(self):
        orders = parse_messages([
            {'id': 1, 'file_name': '2026-08-23 10-00-00.mp3', 'text': 'ганеево бочок индейки два'},
            {'id': 2, 'file_name': '2026-08-23 10-05-00.mp3', 'text': 'ганеево краковская килограмм'},
        ], CATALOG, CLIENTS)
        self.assertEqual(len(orders), 1)
        self.assertIn('тот же клиент', orders[0]['merge_reasons'][0])

    def test_name_time_and_file_time_are_not_compared(self):
        orders = parse_messages([
            {'id': 1, 'file_name': '2026-08-23 10-00-00.mp3', 'text': 'ганеево бочок индейки два'},
            {'id': 2, 'file_name': 'voice.ogg', 'last_modified': 1, 'text': 'ганеево краковская килограмм'},
        ], CATALOG, CLIENTS)
        self.assertEqual(len(orders), 1)  # same client; the times say nothing

    def test_recording_time(self):
        self.assertEqual(recorded_at('audio_2026-08-23_21-37-42.ogg'), recorded_at('2026-08-23 21-37-42.mp3'))
        self.assertEqual(recorded_at('20260823_213742.m4a'), recorded_at('2026-08-23 21-37-42.mp3'))
        self.assertEqual(recorded_at('voice.ogg', 1756000000000), 1756000000)
        self.assertIsNone(recorded_at('voice.ogg'))


class ProcessOrdersRouteTest(unittest.TestCase):
    def test_route(self):
        from server import app
        products = [SimpleNamespace(id=p['id'], name=p['name'], article=None, code=None,
                                    storage_unit=p.get('storage_unit'), report_unit=None,
                                    nomenclature_type=p.get('nomenclature_type'), max_quantity=None)
                    for p in CATALOG]
        clients = [SimpleNamespace(id=c['id'], name=c['name'], code=None, public_name=c.get('public_name'))
                   for c in CLIENTS]
        branch = SimpleNamespace(get_order_settings=lambda: {'merge_window_min': 30})
        with patch('repositories.EmployeeRepository.get_by_id', return_value=branch), \
             patch('repositories.NomenclatureRepository.get_by_employee', return_value=products), \
             patch('repositories.ClientRepository.get_by_employee', return_value=clients), \
             patch('repositories.VoiceDictionaryRepository.get_data', return_value=[]), \
             patch('requests.post', side_effect=AssertionError('no network')):
            response = app.test_client().post('/api/process-orders', json={
                'employee_id': 'e', 'messages': MergeTest().messages()})
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual([o['message_ids'] for o in response.json['orders']], [['a', 'b'], ['c'], ['d']])

    def test_route_needs_branch(self):
        from server import app
        response = app.test_client().post('/api/process-orders', json={'messages': [{'text': 'x'}]})
        self.assertEqual(response.status_code, 400)
        self.assertIn('филиал', response.json['error'])


class FastIndexTest(unittest.TestCase):
    def test_same_ranking_as_frozen_index(self):
        import random
        from catalog_matching import CatalogIndex
        from order_pipeline import FastCatalogIndex
        rng = random.Random(3)
        words = ['сосиски', 'колбаса', 'рулет', 'зельц', 'индейки', 'куриные', 'в/у', 'газ', '0.300', 'ПОЛОВИНКА']
        catalog = CATALOG + [{'id': f'r{i}', 'name': ' '.join(rng.sample(words, rng.randint(1, 4)))}
                             for i in range(300)]
        frozen, fast = CatalogIndex(catalog), FastCatalogIndex(catalog)
        for query in ['бачок индейки', 'рулет цб в у', 'зель с', '', 'по 0.3'] + [
                ' '.join(rng.sample(words, 2)) for _ in range(20)]:
            with self.subTest(query=query):
                self.assertEqual(fast.rank(query), frozen.rank(query))


class SettingsRouteTest(unittest.TestCase):
    def test_save_merges_and_cleans(self):
        from server import app
        branch = SimpleNamespace(get_order_settings=lambda: clean({'max_kg': 20}))
        with patch('repositories.EmployeeRepository.get_by_id', return_value=branch), \
             patch('repositories.EmployeeRepository.update') as update:
            response = app.test_client().put('/api/employees/e/order-settings',
                                             json={'plausibility': False, 'unknown': 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json['settings']['plausibility'], response.json['settings']['max_kg']),
                         (False, 20))
        self.assertNotIn('unknown', update.call_args.kwargs['order_settings'])
        # only own choices are stored: defaults changed later still apply
        self.assertEqual(json.loads(update.call_args.kwargs['order_settings']), {'plausibility': False, 'max_kg': 20})

    def test_product_limit_must_be_positive(self):
        from server import app
        response = app.test_client().put('/api/employees/e/nomenclature/n/limit', json={'max_quantity': -3})
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
