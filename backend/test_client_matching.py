import unittest

from client_matching import alias_conflicts, client_profile, detect_client

CATALOG = [{'id': 'b', 'name': 'Бочок индейки', 'storage_unit': 'кг'},
           {'id': 's', 'name': 'Сосиски Барбекю ОХЛ', 'storage_unit': 'кг'}]
CLIENTS = [
    {'id': 'n', 'name': 'Нурыев Р.Н. ИП', 'public_name': 'ИП Нурыев Ринат Наилевич'},
    {'id': 'r', 'name': 'РОМАШКА ООО', 'public_name': 'ООО Ромашка'},
    {'id': 'g', 'name': 'Ногуманова Л.Л.(г.Лениногорск, ул.Степная,1)',
     'public_name': 'ИП Ногуманова Люция Людвиговна', 'code': '012873'},
]


class ClientMatchingTest(unittest.TestCase):
    def test_profile_of_1c_names(self):
        profile = client_profile(CLIENTS[2])
        self.assertEqual(profile['keys'], [['ногуманова']])
        self.assertEqual(set(profile['support']), {'люция', 'людвиговна'})
        self.assertEqual(set(profile['address']), {'лениногорск', 'степная'})
        # «ИП Мифтяева И.Р. г.Нижнекамск, ул.Баки Урманче» — address without brackets
        profile = client_profile({'id': 1, 'name': 'ИП Мифтяева И.Р. г.Нижнекамск, ул.Баки Урманче, д.15'})
        self.assertEqual(profile['keys'], [['мифтяева']])
        self.assertIn('нижнекамск', profile['address'])

    def test_surname_alone_is_enough(self):
        client = detect_client('ногуманова бочок индейки два', CLIENTS, CATALOG)
        self.assertEqual((client['client_id'], client['needs_review']), ('g', False))
        self.assertEqual(client['confidence'], .85)

    def test_inflected_surname_and_stt_vowel(self):
        client = detect_client('добавь нуреевым сосиски барбекю одну штуку', CLIENTS, CATALOG)
        self.assertEqual((client['client_id'], client['needs_review']), ('n', False))

    def test_manual_short_form_has_priority(self):
        dictionary = [{'item_id': 'r', 'original': 'РОМАШКА ООО', 'category': 'client',
                       'variants': [{'variant': 'магазин у дома'}, {'variant': '001234'}]}]
        client = detect_client('магазин у дома бочок индейки два', CLIENTS, CATALOG, dictionary)
        self.assertEqual((client['client_id'], client['matched_by'], client['confidence']),
                         ('r', 'dictionary', 1.0))
        # numeric 1C codes are not spoken short forms
        self.assertIsNone(detect_client('заказ 001234 бочок два', CLIENTS, CATALOG, dictionary)['client_id'])

    def test_same_surname_needs_review_city_settles_it(self):
        clients = CLIENTS + [{'id': 'g2', 'name': 'Ногуманова А.А.(г.Бугульма, ул.Ленина,5)'}]
        client = detect_client('ногуманова бочок индейки два', clients, CATALOG)
        self.assertTrue(client['needs_review'])
        self.assertEqual({c['id'] for c in client['candidates'][:2]}, {'g', 'g2'})
        client = detect_client('ногуманова бугульма бочок индейки два', clients, CATALOG)
        self.assertEqual((client['client_id'], client['needs_review']), ('g2', False))
        self.assertEqual(alias_conflicts(clients)[0]['said'], 'ногуманова')

    def test_only_address_goes_to_review(self):
        client = detect_client('лениногорск степная бочок индейки два', CLIENTS, CATALOG)
        self.assertEqual((client['client_id'], client['needs_review'], client['matched_by']), ('g', True, 'address'))
        # one address word or a first name alone is not a client
        self.assertIsNone(detect_client('степная бочок индейки два', CLIENTS, CATALOG)['client_id'])
        self.assertIsNone(detect_client('люция бочок индейки два', CLIENTS, CATALOG)['client_id'])

    def test_misheard_first_vowel_and_split_surname(self):
        clients = [{'id': 'd', 'name': 'Деданина О.С.ИП', 'public_name': 'ИП Деданина О.С.'},
                   {'id': 'x', 'name': 'Дегтярев А.А. ИП'}]
        for text in ('диданина азнакаево бочок индейки два', 'деда нина бочок индейки два'):
            with self.subTest(text=text):
                self.assertEqual(detect_client(text, clients, CATALOG)['client_id'], 'd')
        # too far from any client: nothing is guessed, the manager teaches the short form
        self.assertIsNone(detect_client('дидайна бочок индейки два', clients, CATALOG)['client_id'])
        taught = [{'category': 'client', 'item_id': 'd', 'original': 'Деданина О.С.ИП',
                   'variants': [{'variant': 'дидайна'}]}]
        client = detect_client('дидайна бугульма бочок индейки два', clients, CATALOG, taught)
        self.assertEqual((client['client_id'], client['confidence']), ('d', 1.0))

    def test_client_named_after_products(self):
        client = detect_client('бочок индейки два это для нурыева', CLIENTS, CATALOG)
        self.assertEqual((client['client_id'], client['needs_review']), ('n', False))


if __name__ == '__main__':
    unittest.main()
