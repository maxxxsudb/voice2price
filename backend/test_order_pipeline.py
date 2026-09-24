import unittest

from spoken_quantity import find_quantities, quantity_is_spoken
from order_segmenter import segment
from order_pipeline import decide, lexical_decision, plausible, usable_catalog, name_covers

CATALOG = [
    {'id': 'bochok', 'name': 'Бочок индейки к/в', 'storage_unit': 'кг'},
    {'id': 'krakov', 'name': 'Краков   п/к ( газ )', 'storage_unit': 'кг'},
    {'id': 'serv', 'name': 'Сервелат "Венский " п/к', 'storage_unit': 'кг'},
    {'id': 'serv_gas', 'name': 'Сервелат "Венский " п/к  газ', 'storage_unit': 'кг'},
    {'id': 'rulet', 'name': 'Рулет из мяса индейки запеченный в/у', 'storage_unit': 'кг'},
    {'id': 'rulet_half', 'name': 'Рулет из мяса индейки запеченный в/у ( ПОЛОВИНКА )', 'storage_unit': 'кг'},
    {'id': 'rulet_300', 'name': 'Рулет из мяса индейки запеченный ( 0.300 )', 'storage_unit': 'шт'},
    {'id': 'rulet_fil', 'name': 'Рулет из мяса индейки "Филейный" запеченный', 'storage_unit': 'кг'},
    {'id': 'rulet_cb', 'name': 'Рулет из мяса ЦБ запеченный в/у', 'storage_unit': 'кг'},
    {'id': 'zelc250', 'name': 'Зельц " Говяжий " 250 гр', 'storage_unit': 'шт'},
    {'id': 'zelc2500', 'name': 'Зельц " Говяжий " 2500 гр', 'storage_unit': 'кг'},
    {'id': 'studen_nb', 'name': 'Студень " Из индейки  2.500 гр. НЕ БРАТЬ', 'storage_unit': 'кг'},
    {'id': 'transport', 'name': 'Транспортные услуги', 'storage_unit': 'шт', 'nomenclature_type': 'Услуги'},
]


class SpokenQuantityTest(unittest.TestCase):
    def test_forms(self):
        cases = {'кило двести': 1.2, 'два шестьсот': 2.6, 'ноль восемь': 0.8, 'полтора': 1.5,
                 'три с половиной': 3.5, 'четыре штуки': 4, 'килограмм': 1, 'триста грамм': 0.3,
                 'кило сто': 1.1, 'два и семь': 2.7, 'ноль двадцать пять': 0.25}
        for text, value in cases.items():
            with self.subTest(text=text):
                self.assertEqual([q['value'] for q in find_quantities(text)], [value])

    def test_not_a_quantity(self):
        self.assertEqual(find_quantities('ноль процентный прайс'), [])

    def test_units(self):
        self.assertEqual(find_quantities('четыре штуки')[0]['unit'], 'шт')
        self.assertEqual(find_quantities('две палки')[0]['unit'], 'уп')
        self.assertEqual(find_quantities('кило двести')[0]['unit'], 'кг')

    def test_quantity_must_be_spoken(self):
        self.assertTrue(quantity_is_spoken(1.8, 'буженаль кило восемьсот'))
        self.assertFalse(quantity_is_spoken(800, 'буженаль кило восемьсот'))


class SegmenterTest(unittest.TestCase):
    def test_header_and_quantities(self):
        items = segment('мустафино лениногорск место тридцать один бачок индейки килограмм '
                        'краковская кило двести', CATALOG)
        self.assertEqual([(i['spoken_name'], i['quantity'], i['explicit_unit']) for i in items],
                         [('бочок индейки', 1, 'кг'), ('краковская', 1.2, 'кг')])

    def test_quantity_after_pause_belongs_to_previous_product(self):
        items = segment('рулет индейка запеченный\nдевять рулет цб запеченный в вакууме девять', CATALOG)
        self.assertEqual([i['quantity'] for i in items], [9, 9])

    def test_pack_weight_is_not_quantity(self):
        items = segment('ветчина экстра порционная по ноль три ноль три', CATALOG + [
            {'id': 'v', 'name': 'Ветчина ЭКСТРА в/у', 'storage_unit': 'кг'}])
        self.assertTrue(items[0].get('needs_review'))

    def test_comment_attaches_to_previous(self):
        items = segment('рулет утиный запеченный килограмм комментарий рулеты из индейки только большие',
                        CATALOG + [{'id': 'u', 'name': 'Рулет из мяса УТКИ запеченый', 'storage_unit': 'кг'}])
        self.assertEqual(len(items), 1)
        self.assertIn('больш', items[0]['comments'])


class CommentRoutingTest(unittest.TestCase):
    def test_comment_goes_to_the_product_it_names(self):
        catalog = CATALOG + [{'id': 'u', 'name': 'Рулет из мяса УТКИ запеченый', 'storage_unit': 'кг'},
                             {'id': 'i', 'name': 'Индейка "Французская" к/в', 'storage_unit': 'кг'}]
        items = segment('рулет индейка запеченный ноль восемь рулет утиный запеченный килограмм '
                        'комментарий рулеты из индейки только большие', catalog)
        self.assertIn('больш', items[0]['comments'])
        self.assertEqual(items[1]['comments'], '')

    def test_new_product_after_comment_is_a_new_line(self):
        catalog = CATALOG + [{'id': 't', 'name': 'Тушка из мяса утки к/в', 'storage_unit': 'кг'},
                             {'id': 'z', 'name': 'Зразы из индейки с сыром и луком', 'storage_unit': 'кг'}]
        items = segment('тушка утки четыре килограмма комментарий тушка утки строго две штуки самая большая '
                        'и заморозка зразы из индейки с сыром два', catalog)
        self.assertEqual([(i['spoken_name'][:5], i['quantity']) for i in items], [('тушка', 4), ('зразы', 2)])


class DecisionTest(unittest.TestCase):
    def line(self, spoken, quantity, unit=None, source=None):
        item = {'spoken_name': spoken, 'quantity': quantity, 'explicit_unit': unit,
                'source_text': source or f'{spoken}'}
        cands = usable_catalog(CATALOG)
        return decide(item, cands, lexical_decision(item, cands))

    def test_confident_line_is_confirmed_with_catalog_unit(self):
        line = self.line('бочок индейки', 2, source='бочок индейки два')
        self.assertFalse(line['needs_review'], line['review_reason'])
        self.assertEqual((line['nomenclature_id'], line['unit'], line['unit_source']), ('bochok', 'кг', 'catalog'))

    def test_packaging_not_said_needs_review(self):
        line = self.line('сервелат венский', 5, source='сервелат венский пять')
        self.assertTrue(line['needs_review'])

    def test_unspoken_portion_or_brand_is_not_chosen(self):
        line = self.line('рулет индейка запеченный', 9, source='рулет индейка запеченный девять')
        self.assertEqual(line['nomenclature_id'], 'rulet')
        self.assertFalse(line['needs_review'], line['review_reason'])

    def test_weight_vs_portion(self):
        self.assertEqual(self.line('зельц говяжий весовой', 2.5, source='зельц говяжий весовой два с половиной')['nomenclature_id'], 'zelc2500')
        self.assertEqual(self.line('зельц говяжий порционный', 2, 'шт', 'зельц говяжий порционный две штуки')['nomenclature_id'], 'zelc250')

    def test_meat_kind_is_checked(self):
        line = self.line('рулет запеченный куриный в у', 2.7, source='рулет запеченный куриный в у два и семь')
        self.assertEqual(line['nomenclature_id'], 'rulet_cb')

    def test_do_not_take_and_services_are_excluded(self):
        ids = {p['id'] for p in usable_catalog(CATALOG)}
        self.assertNotIn('studen_nb', ids)
        self.assertNotIn('transport', ids)

    def test_model_answer_must_be_a_candidate(self):
        item = {'spoken_name': 'бочок индейки', 'quantity': 1, 'source_text': 'бочок индейки килограмм'}
        line = decide(item, usable_catalog(CATALOG), {'name': 'Крыло индейки к/в'})
        self.assertTrue(line['needs_review'])
        self.assertIsNone(line['nomenclature_id'])

    def test_invented_quantity_is_flagged(self):
        item = {'spoken_name': 'бочок индейки', 'quantity': 800, 'source_text': 'бочок индейки кило восемьсот'}
        line = decide(item, usable_catalog(CATALOG), {'name': 'Бочок индейки к/в'})
        self.assertTrue(line['needs_review'])

    def test_parse_order_end_to_end(self):
        from order_pipeline import parse_order
        lines = parse_order('ганеево альметьевск строителей двадцать два бачок индейки кило двести '
                            'сервелат венский полтора', CATALOG)
        self.assertEqual([(l['nomenclature_id'], l['quantity'], l['needs_review']) for l in lines],
                         [('bochok', 1.2, False), ('serv', 1.5, True)])

    def test_unknown_word_blocks_confirmation(self):
        self.assertEqual(name_covers('северолатвенский газ', 'Сервелат "Венский " п/к  газ'), ['северолатвенский'])


if __name__ == '__main__':
    unittest.main()
