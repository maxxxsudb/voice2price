"""Check a branch catalog before orders are parsed: positions a voice order cannot
tell apart always end up in review, so the manager should learn about them early
(after import, in the branch card and on the upload screen), not per order.
"""
import re
from collections import defaultdict

from order_pipeline import usable_catalog
from order_segmenter import normalize

LEGAL_FORM = re.compile(r'\b(ооо|оао|зао|пао|ао|ип|чп|тоо|индивидуальный предприниматель)\b')


def _ref(p):
    return {'id': str(p.get('id')), 'name': p.get('name') or ''}


def _spoken_key(name):
    """What a customer can say: the name without numbers."""
    return ' '.join(w for w in normalize(name).split() if not w[0].isdigit())


def _issue(level, kind, message, items):
    return {'level': level, 'kind': kind, 'message': message, 'items': [_ref(p) for p in items]}


def validate_catalog(catalog_rows, dictionary_entries=None, clients=None, settings=None):
    issues = []
    catalog = usable_catalog(catalog_rows)
    used = {id(p) for p in catalog}
    excluded = [p for p in catalog_rows if id(p) not in used]

    by_name, by_spoken = defaultdict(list), defaultdict(list)
    for p in catalog:
        by_name[normalize(p['name'])].append(p)
        by_spoken[_spoken_key(p['name'])].append(p)
    for group in by_name.values():
        if len(group) > 1:
            issues.append(_issue(
                'error', 'duplicate_name',
                f'Одинаковое название у {len(group)} позиций с разными ID: голосом их не различить, '
                'каждая такая строка уйдёт на проверку. Уберите дубль в 1С или переименуйте.', group))
    for key, group in by_spoken.items():
        names = {normalize(p['name']) for p in group}
        if key and len(group) > 1 and len(names) > 1:
            issues.append(_issue(
                'warning', 'differs_by_numbers',
                'Названия отличаются только числами (фасовка, вес): если клиент не назовёт их, '
                'строка уйдёт на проверку.', group))

    for field, title in (('article', 'артикул'), ('code', 'код')):
        seen = defaultdict(list)
        for p in catalog:
            value = str(p.get(field) or '').strip()
            if value:
                seen[value.lower()].append(p)
        for value, group in seen.items():
            if len(group) > 1:
                issues.append(_issue('warning', f'duplicate_{field}',
                                     f'Одинаковый {title} «{value}» у разных позиций.', group))

    names = {normalize(p['name']): p for p in catalog}
    variants = defaultdict(set)
    for entry in dictionary_entries or []:
        if entry.get('category') != 'nomenclature':
            continue
        original = normalize(entry.get('original'))
        for row in entry.get('variants') or []:
            variant = normalize(row.get('variant'))
            if variant and re.search(r'[а-яa-z]', variant) and variant != original:
                variants[variant].add(original)
    for variant, originals in variants.items():
        targets = [names[o] for o in originals if o in names]
        if len(targets) > 1:
            issues.append(_issue(
                'warning', 'ambiguous_variant',
                f'Вариант произношения «{variant}» записан у нескольких позиций и поэтому не применяется.',
                targets))
        if variant in names and any(names[variant] is not t for t in targets):
            issues.append(_issue(
                'warning', 'variant_is_other_name',
                f'Вариант произношения «{variant}» совпадает с названием другой позиции.',
                [names[variant]] + targets))

    by_client = defaultdict(list)
    for c in clients or []:
        key = ' '.join(LEGAL_FORM.sub(' ', normalize(c.get('name'))).split())
        if key:
            by_client[key].append(c)
    for group in by_client.values():
        if len(group) > 1:
            issues.append(_issue('warning', 'duplicate_client',
                                 f'Одинаковое название у {len(group)} клиентов: клиента не определить по голосу.',
                                 group))
    from client_matching import alias_conflicts
    duplicates = {tuple(sorted(str(c['id']) for c in g)) for g in by_client.values() if len(g) > 1}
    for conflict in alias_conflicts(clients, dictionary_entries):
        if tuple(c['id'] for c in conflict['clients']) in duplicates:
            continue
        issues.append({'level': 'info', 'kind': 'client_alias_conflict',
                       'message': f'«{conflict["said"]}» подходит {len(conflict["clients"])} клиентам: '
                                  'без города/улицы клиент уйдёт на проверку. Добавьте каждому своё '
                                  'сокращение в словарь (категория «Клиент»).',
                       'items': conflict['clients']})

    # realistic quantity is checked only where a limit is set
    from order_settings import clean, quantity_limit
    settings = clean(settings)
    if settings['plausibility']:
        no_limit = [p for p in catalog if p.get('storage_unit') in ('кг', 'шт')
                    and quantity_limit(p, p.get('storage_unit'), settings) is None]
        if no_limit:
            issues.append(_issue(
                'info', 'no_limit',
                f'Без реалистичного максимума: {len(no_limit)} поз. По ним большое количество '
                '(«сосиски пятьсот») не проверяется и граммы не распознаются. Задайте максимум у позиции '
                'или общий лимит для кг / шт в «Настройках разбора».', no_limit[:20]))

    if excluded:
        issues.append(_issue('info', 'excluded',
                             f'Не участвуют в разборе: {len(excluded)} (услуги, «НЕ БРАТЬ», '
                             'единица руб/м2).', excluded[:20]))
    counts = {level: sum(1 for i in issues if i['level'] == level) for level in ('error', 'warning', 'info')}
    return {'issues': issues, 'counts': counts, 'catalog_size': len(catalog)}
