"""Офлайн-проверка разбора заказа на размеченных расшифровках (без облака).

Эталон и расшифровки лежат только в local/_eval/2026-09-24-test20/ (не в Git):
  sample10.json  — 10 записей, на которых правила настраивались;
  holdout10.json — 10 записей, проверенных один раз после заморозки правил;
  catalog.json   — справочник сотрудника на момент проверки.
В каждом файле: строки SpeechKit, эталон позиций и ответ прежнего разбора (prod).

  python experiments/voice-order-20260924/evaluate_offline.py
"""
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from catalog_matching import normalize  # noqa: E402
from order_pipeline import parse_order  # noqa: E402

DATA = ROOT / 'local' / '_eval' / '2026-09-24-test20'


def match_gold(name, gold, used):
    best, best_score = None, 0.45
    for i, g in enumerate(gold):
        if i in used:
            continue
        r = SequenceMatcher(None, normalize(name), normalize(g['q'])).ratio()
        if r > best_score:
            best, best_score = i, r
    return best


def score(sample, outputs):
    m = dict(gold=0, found=0, qty_ok=0, auto_ok=0, auto_wrong=0, review=0, missing=0, extra=0)
    wrong = []
    for rec, d in sample.items():
        gold, rows, align = d['gold'], outputs[rec]['rows'], outputs[rec]['align']
        m['gold'] += len(gold)
        seen = set()
        for (name, pid, qty, unit, review), g in zip(rows, align):
            if g is None:
                m['extra'] += 1
                if not review:
                    m['auto_wrong'] += 1
                    wrong.append((rec, 'лишняя строка', name))
                continue
            seen.add(g)
            G = gold[g]
            m['found'] += 1
            qty_ok = (qty is None and G['qty'] is None) or (
                qty is not None and G['qty'] is not None and abs(qty - G['qty']) < 1e-9)
            m['qty_ok'] += qty_ok
            if review:
                m['review'] += 1
                continue
            unit_ok = not G.get('unit') or unit is None or unit == G['unit']
            ok = pid in G['ids'] and not G.get('amb') and not G.get('none') and qty_ok and unit_ok
            m['auto_ok'] += ok
            m['auto_wrong'] += not ok
            if not ok:
                wrong.append((rec, G['q'], G['qty'], '->', name, qty, unit))
        m['missing'] += len(gold) - len(seen)
    return m, wrong


def main():
    catalog = json.loads((DATA / 'catalog.json').read_text(encoding='utf-8'))
    for part in ('sample10', 'holdout10'):
        sample = json.loads((DATA / f'{part}.json').read_text(encoding='utf-8'))
        prod = {k: {'rows': [r[:5] for r in v['prod']], 'align': v['prod_align']} for k, v in sample.items()}
        new = {}
        for rec, d in sample.items():
            lines, used, align = parse_order('\n'.join(d['lines']), catalog), set(), []
            for line in lines:
                a = match_gold(line['spoken_name'], d['gold'], used)
                align.append(a)
                used.add(a)
            new[rec] = {'rows': [[l['name'], l['nomenclature_id'], l['quantity'], l['unit'], l['needs_review']]
                                 for l in lines], 'align': align}
        for label, out in (('прежний разбор (YandexGPT)', prod), ('новый разбор (правила)', new)):
            m, wrong = score(sample, out)
            print(f'{part} · {label}: позиций {m["gold"]}, найдено {m["found"]}, количество верно {m["qty_ok"]}, '
                  f'авто и верно {m["auto_ok"]}, авто и НЕВЕРНО {m["auto_wrong"]}, на проверку {m["review"]}, '
                  f'пропущено {m["missing"]}, лишних {m["extra"]}')
            for w in wrong:
                print('    авто-ошибка:', *w)


if __name__ == '__main__':
    main()
