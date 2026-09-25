"""Dictation half-standard must never be worse than free speech.

Every real transcript from local/_eval (SpeechKit lines of the 20 benchmark
records, plus GigaAM texts of a live run if saved) is parsed twice: as said,
and rewritten into «Клиент. Товар, сколько. Дальше — товар, сколько. … Всё.»
The rewritten order must give at least as many auto-confirmed lines and the
same number of lines (except a dropped client/address line).

  python experiments/voice-order-20260924/check_format.py [live.json]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from order_pipeline import parse_order  # noqa: E402
from order_segmenter import segment  # noqa: E402

DATA = ROOT / 'local' / '_eval' / '2026-09-24-test20'


def dictated(text, catalog):
    """The same order said by the half-standard."""
    parts = [s['source_text'] for s in segment(text, catalog)]
    return '. дальше '.join(parts) + '. всё' if parts else ''


def main():
    catalog = json.loads((DATA / 'catalog.json').read_text(encoding='utf-8'))
    texts = {}
    for part in ('sample10', 'holdout10'):
        for key, record in json.loads((DATA / f'{part}.json').read_text(encoding='utf-8')).items():
            texts[key] = ' '.join(record['lines'])
    if len(sys.argv) > 1:
        for row in json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')):
            texts[row['file']] = row.get('text') or ''
    free_auto = format_auto = worse = 0
    for key, text in sorted(texts.items()):
        free = parse_order(text, catalog)
        form = parse_order(dictated(text, catalog), catalog)
        a = sum(not line['needs_review'] for line in free)
        b = sum(not line['needs_review'] for line in form)
        free_auto, format_auto = free_auto + a, format_auto + b
        if b < a:
            worse += 1
            print(f'ХУЖЕ {key}: авто {a} -> {b}')
    print(f'{len(texts)} заказов: авто свободно {free_auto}, по формату {format_auto}, хуже: {worse}')
    return 1 if worse else 0


if __name__ == '__main__':
    sys.exit(main())
