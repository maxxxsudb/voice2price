"""Re-import of nomenclature and clients: update in place, no duplicates.
Runs the real importers on a temporary SQLite database."""
import os
import tempfile
import unittest
from unittest.mock import patch

import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from catalog_sync import client_keys, nomenclature_keys, plan


def write_xlsx(path, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['name'] + [f'c{i}' for i in range(1, 23)])
    for row in rows:
        ws.append(row)
    wb.save(path)


def product(name, article=None, code=None, unit='кг'):
    # name, article, weight_unit, den, weight, num, type, report_unit, storage_unit, gtin, code
    return [name, article, None, None, None, None, 'Товар', unit, unit, None, code]


class PlanTest(unittest.TestCase):
    def test_match_by_code_then_name(self):
        existing = [{'id': 'a', 'name': 'Бочок', 'code': '001'},
                    {'id': 'b', 'name': 'Краков', 'code': None},
                    {'id': 'b2', 'name': 'Краков', 'code': None},   # duplicate of an old import
                    {'id': 'c', 'name': 'Снято с продажи', 'code': '009'}]
        incoming = [{'name': 'Бочок индейки (новое название)', 'code': '001'},
                    {'name': 'краков', 'code': None},
                    {'name': 'Новинка', 'code': '010'}]
        matches, new, removed = plan(existing, incoming, nomenclature_keys)
        self.assertEqual([m[0] for m in matches], ['a', 'b'])
        self.assertEqual([r['name'] for r in new], ['Новинка'])
        self.assertEqual(removed, ['b2', 'c'])

    def test_same_name_in_file_twice_uses_each_row_once(self):
        existing = [{'id': 'x', 'name': 'Ромашка', 'code': None}]
        matches, new, _ = plan(existing, [{'name': 'Ромашка'}, {'name': 'Ромашка'}], client_keys)
        self.assertEqual((len(matches), len(new)), (1, 1))


class ReimportTest(unittest.TestCase):
    def setUp(self):
        import models_db
        self.folder = tempfile.TemporaryDirectory()
        self.engine = create_engine(f'sqlite:///{self.folder.name}/test.db')
        models_db.Base.metadata.create_all(self.engine)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        self.patches = [patch('repositories.get_session', self.Session),
                        patch('repositories.close_session', self.Session.remove)]
        for p in self.patches:
            p.start()
        from repositories import EmployeeRepository
        EmployeeRepository.create('kazan', 'Иванов')

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.Session.remove()
        self.engine.dispose()  # Windows cannot delete an open SQLite file
        self.folder.cleanup()

    def import_products(self, rows):
        from import_nomenclature import import_nomenclature
        path = os.path.join(self.folder.name, 'n.xlsx')
        write_xlsx(path, rows)
        return import_nomenclature('kazan', path)

    def test_nomenclature_reimport(self):
        from repositories import NomenclatureRepository, VoiceDictionaryRepository
        self.import_products([product('Бочок индейки к/в', 'A1', '001'), product('Краков п/к')])
        first = {p.name: p.id for p in NomenclatureRepository.get_by_employee('kazan')}
        NomenclatureRepository.set_max_quantity('kazan', first['Бочок индейки к/в'], 5)
        entry = next(e for e in VoiceDictionaryRepository.get_by_employee('kazan')
                     if e.original == 'Бочок индейки к/в')
        VoiceDictionaryRepository.add_variant(entry.id, 'бачок')

        result = self.import_products([product('Бочок индейки к/в (новое)', 'A1', '001'),
                                       product('Сервелат Венский'), product('')])
        self.assertEqual((result['updated'], result['created'], result['removed']), (1, 1, 1))
        items = {p.name: p for p in NomenclatureRepository.get_by_employee('kazan')}
        self.assertEqual(set(items), {'Бочок индейки к/в (новое)', 'Сервелат Венский'})
        renamed = items['Бочок индейки к/в (новое)']
        self.assertEqual((renamed.id, renamed.max_quantity), (first['Бочок индейки к/в'], 5))
        entries = [e for e in VoiceDictionaryRepository.get_by_employee('kazan') if e.item_id == renamed.id]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].original, 'Бочок индейки к/в (новое)')
        self.assertIn('бачок', {v.variant for v in entries[0].variants})

        # the same file again changes nothing; «Краков» returns when it is back in the file
        again = self.import_products([product('Бочок индейки к/в (новое)', 'A1', '001'),
                                      product('Сервелат Венский'), product('Краков п/к')])
        self.assertEqual((again['updated'], again['created'], again['restored'], again['removed']), (2, 0, 1, 0))
        items = {p.name: p.id for p in NomenclatureRepository.get_by_employee('kazan')}
        self.assertEqual(len(items), 3)
        self.assertEqual(items['Краков п/к'], first['Краков п/к'])

    def test_clients_reimport(self):
        from import_clients import import_clients
        from repositories import ClientRepository
        path = os.path.join(self.folder.name, 'c.xlsx')
        write_xlsx(path, [['ООО Ромашка', 'K1'], ['ИП Мустафина', None]])
        import_clients('kazan', path)
        ids = {c.name: c.id for c in ClientRepository.get_by_employee('kazan')}
        write_xlsx(path, [['ООО Ромашка (сеть)', 'K1'], ['ИП Мустафина', None]])
        result = import_clients('kazan', path)
        self.assertEqual((result['updated'], result['created'], result['removed']), (2, 0, 0))
        clients = {c.name: c.id for c in ClientRepository.get_by_employee('kazan')}
        self.assertEqual(clients, {'ООО Ромашка (сеть)': ids['ООО Ромашка'], 'ИП Мустафина': ids['ИП Мустафина']})


if __name__ == '__main__':
    unittest.main()
