"""Итог по размеченному review.csv (после run_batch.py).

В колонке «верно» ставьте «да», если строка заказа полностью правильная
(товар, количество, единица), иначе «нет». В «пропущено_позиций» первой
строки файла — сколько позиций заказа система не нашла вовсе.

Главные числа:
- «автоматически и верно» — строки без ручной проверки, которые правильные (конверсия);
- «автоматически, но неверно» — опасные ошибки: должны быть близки к нулю.
"""
import csv
import sys


def main(path):
    with open(path, encoding='utf-8-sig') as fh:
        rows = list(csv.DictReader(fh, delimiter=';'))
    labeled = [r for r in rows if r['верно'].strip().lower() in ('да', 'нет')]
    missed = sum(int(r['пропущено_позиций'] or 0) for r in rows if r['пропущено_позиций'].strip().isdigit())
    auto_ok = sum(r['авто'] == 'да' and r['верно'].lower() == 'да' for r in labeled)
    auto_bad = sum(r['авто'] == 'да' and r['верно'].lower() == 'нет' for r in labeled)
    review = sum(r['авто'] != 'да' for r in labeled)
    lines = len(labeled) + missed
    print(f'Размечено строк: {len(labeled)} из {len(rows)}; пропущенных позиций: {missed}')
    if lines:
        print(f'Автоматически и верно: {auto_ok} ({auto_ok / lines:.0%} всех позиций заказа)')
        print(f'Автоматически, но неверно: {auto_bad} ({auto_bad / lines:.0%})')
        print(f'На проверку менеджеру: {review} ({review / lines:.0%})')


if __name__ == '__main__':
    main(sys.argv[1])
