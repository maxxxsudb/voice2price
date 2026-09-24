"""Прогон голосовых из local/ через работающий backend (docker compose up).

Все результаты (расшифровки, адреса клиентов, заказы) пишутся ТОЛЬКО в
local/_eval/…, который исключён из Git (.gitignore: local/). Ничего не
отправляется никуда, кроме вашего backend (а он — в ваш Яндекс SpeechKit).

Примеры:
  python experiments/voice-order-20260924/run_batch.py --sample 10
  python experiments/voice-order-20260924/run_batch.py --all
  python experiments/voice-order-20260924/run_batch.py --files "ЦГ_220826_КурушинИлья/ЦГ_220826_КурушинИлья-14.mp3"

После прогона откройте review.csv в Excel, заполните колонки «верно» и,
если нужно, «правильный_id»/«правильное_количество», затем:
  python experiments/voice-order-20260924/score_review.py local/_eval/<папка>/review.csv
"""
import argparse
import csv
import json
import random
import sys
import time
import uuid
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FOLDER = ROOT / 'local' / 'Примеры входящих голосовых, и справочники'


def post_file(url, path, fields):
    boundary = uuid.uuid4().hex
    body = bytearray()
    for key, value in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
             f'Content-Type: audio/mpeg\r\n\r\n').encode() + path.read_bytes() + b'\r\n'
    body += f'--{boundary}--\r\n'.encode()
    req = urllib.request.Request(url, data=bytes(body), method='POST',
                                 headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(req, timeout=900) as resp:
        return json.loads(resp.read().decode('utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--folder', default=str(DEFAULT_FOLDER))
    ap.add_argument('--backend', default='http://localhost:5000')
    ap.add_argument('--employee', default='Cigan')
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--sample', type=int, help='случайные N файлов')
    group.add_argument('--all', action='store_true')
    group.add_argument('--files', nargs='+', help='пути относительно --folder')
    ap.add_argument('--seed', type=int, default=20260924)
    args = ap.parse_args()

    folder = Path(args.folder)
    if 'local' not in folder.resolve().parts:
        sys.exit('Папка с примерами должна быть внутри local/ (она не попадает в Git).')
    files = sorted(p for p in folder.rglob('*.mp3') if p.stat().st_size > 20_000)
    if args.files:
        files = [folder / f for f in args.files]
    elif args.sample:
        files = random.Random(args.seed).sample(files, min(args.sample, len(files)))

    out = ROOT / 'local' / '_eval' / datetime.now().strftime('%Y%m%d-%H%M%S')
    out.mkdir(parents=True, exist_ok=True)
    rows, auto, total = [], 0, 0
    for n, path in enumerate(files, 1):
        rel = path.relative_to(folder).as_posix()
        started = time.monotonic()
        try:
            data = post_file(f'{args.backend}/api/recognize', path,
                             {'employee_id': args.employee, 'process_llm': 'true'})
        except Exception as exc:  # keep going, record the failure
            data = {'error': str(exc)}
        seconds = round(time.monotonic() - started, 1)
        (out / (rel.replace('/', '__') + '.json')).write_text(
            json.dumps({'file': rel, 'seconds': seconds, **data}, ensure_ascii=False, indent=1), encoding='utf-8')
        items = data.get('order_items') or []
        print(f'[{n}/{len(files)}] {rel}: {len(items)} строк, {seconds} с'
              + (f' ОШИБКА: {data.get("error") or data.get("llm_error")}' if data.get('error') or data.get('llm_error') else ''))
        for i, item in enumerate(items, 1):
            total += 1
            auto += not item.get('needs_review')
            rows.append({
                'файл': rel, 'строка': i, 'расшифровка': data.get('text', '') if i == 1 else '',
                'сказано': item.get('source_text') or '', 'товар': item.get('name'),
                'id': item.get('nomenclature_id') or '', 'количество': item.get('quantity'),
                'ед': item.get('unit') or '', 'авто': 'да' if not item.get('needs_review') else 'нет',
                'причина_проверки': item.get('review_reason') or '', 'комментарий': item.get('comments') or '',
                'верно': '', 'правильный_id': '', 'правильное_количество': '', 'пропущено_позиций': '',
            })
    with open(out / 'review.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ['файл'], delimiter=';')
        writer.writeheader()
        writer.writerows(rows)
    print(f'\nГотово: {len(files)} файлов, {total} строк, без проверки {auto} '
          f'({auto / total:.0%})' if total else '\nГотово: строк нет')
    print(f'Результаты: {out}')


if __name__ == '__main__':
    main()
