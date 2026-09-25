"""Compare the saved pre-overlap GigaAM run with a current batch run."""
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from catalog_matching import normalize  # noqa: E402

DATA = ROOT / 'local' / '_eval' / '2026-09-24-test20'


def align(rows, gold):
    used, result = set(), []
    for row in rows:
        best, score = None, 0.45
        spoken = normalize(row[5])
        for index, item in enumerate(gold):
            if index in used:
                continue
            current = SequenceMatcher(None, spoken, normalize(item['q'])).ratio()
            if current > score:
                best, score = index, current
        result.append(best)
        if best is not None:
            used.add(best)
    return result


def score(samples, outputs):
    metrics = {key: 0 for key in (
        'gold', 'found', 'sku_correct', 'sku_wrong', 'sku_unset',
        'auto_correct', 'auto_false', 'review', 'missing', 'extra')}
    false_cases = []
    for rec, sample in samples.items():
        gold, rows = sample['gold'], outputs[rec]
        matches = align(rows, gold)
        seen = set()
        metrics['gold'] += len(gold)
        for row, match in zip(rows, matches):
            name, pid, qty, unit, review, spoken = row
            if match is None:
                metrics['extra'] += 1
                if not review:
                    metrics['auto_false'] += 1
                    false_cases.append((rec, 'лишняя строка', spoken, name))
                continue
            seen.add(match)
            metrics['found'] += 1
            item = gold[match]
            correct = pid in item['ids'] if item['ids'] else pid is None
            if correct:
                metrics['sku_correct'] += 1
            elif pid is None:
                metrics['sku_unset'] += 1
            else:
                metrics['sku_wrong'] += 1
            if review:
                metrics['review'] += 1
            else:
                safe = correct and not item.get('amb') and not item.get('none')
                if safe:
                    metrics['auto_correct'] += 1
                else:
                    metrics['auto_false'] += 1
                    false_cases.append((rec, item['q'], spoken, name, pid))
        metrics['missing'] += len(gold) - len(seen)
    return metrics, false_cases


def load_samples():
    result = {}
    for name in ('sample10', 'holdout10'):
        result.update(json.loads((DATA / f'{name}.json').read_text(encoding='utf-8')))
    return result


def load_current(folder, samples):
    by_name = {}
    for path in folder.glob('*.json'):
        data = json.loads(path.read_text(encoding='utf-8'))
        by_name[Path(data['file']).name] = data
    result = {}
    for rec, sample in samples.items():
        data = by_name[Path(sample['file']).name]
        result[rec] = [[item['name'], item['nomenclature_id'], item['quantity'], item['unit'],
                        item['needs_review'], item.get('spoken_name') or item.get('source_text') or '']
                       for item in data.get('order_items') or []]
    return result


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: compare_gigaam.py local/_eval/<current-run>')
    samples = load_samples()
    old = json.loads((DATA / 'gigaam20.json').read_text(encoding='utf-8'))
    old_rows = {rec: data['rows'] for rec, data in old.items()}
    current = load_current(Path(sys.argv[1]), samples)
    for label, output in (('before', old_rows), ('current', current)):
        metrics, false_cases = score(samples, output)
        print(label, json.dumps(metrics, ensure_ascii=False, sort_keys=True))
        for case in false_cases:
            print('false_auto', label, *case, sep=' | ')


if __name__ == '__main__':
    main()
