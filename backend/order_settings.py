"""Order parsing options of one branch (branch manager): each check can be turned off.

Stored as JSON in employees.order_settings; missing keys take the defaults below,
so old records and new options work without a migration.
"""
import json

DEFAULTS = {
    # «два кило, точнее три» — replace the previous quantity instead of a new line
    'corrections': True,
    # Realistic quantity. The limit is set per product («Реалистичный максимум
    # в заказе»); branch limits by unit are empty (off) unless the manager sets them.
    'plausibility': True,
    'max_kg': None,
    'max_pcs': None,
    'max_packs': None,
    # «сосиски пятьсот» at a 5 kg limit, unit not said: read as 500 g = 0.5 kg
    'grams_over_limit': True,
    # «зельц двести пятьдесят» with «Зельц 250 гр» in the catalog: 250 is the
    # pack size from the name (it picks the product), not the quantity
    'size_in_name': True,
    # Client from the start of the message, by the branch client list
    'detect_client': True,
    # Consecutive voice messages of one client -> one order
    'merge_messages': True,
    'merge_window_min': 15.0,
}

LIMITS = {'max_kg', 'max_pcs', 'max_packs'}   # positive number or None (no limit)
BOOLEAN = {k for k, v in DEFAULTS.items() if isinstance(v, bool)}
NUMBER = {k for k, v in DEFAULTS.items() if isinstance(v, float)}


def _positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 < value < 1e6


def clean(raw):
    """Known keys only, right types; invalid values fall back to defaults."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or '{}')
        except ValueError:
            raw = {}
    raw = raw if isinstance(raw, dict) else {}
    result = dict(DEFAULTS)
    for key in BOOLEAN:
        if isinstance(raw.get(key), bool):
            result[key] = raw[key]
    for key in NUMBER:
        if _positive(raw.get(key)):
            result[key] = float(raw[key])
    for key in LIMITS:
        if key in raw and (raw[key] is None or _positive(raw[key])):
            result[key] = None if raw[key] is None else float(raw[key])
    return result


def dumps(settings):
    """Store only what differs from the defaults, so a later change of a default
    reaches every branch that did not choose its own value."""
    changed = {k: v for k, v in clean(settings).items() if v != DEFAULTS[k]}
    return json.dumps(changed, ensure_ascii=False, sort_keys=True)


def quantity_limit(product, unit, settings):
    """Limit for one line: the product's own max_quantity (set in its storage unit,
    so only for a line in that unit), else the branch default by unit."""
    own = (product or {}).get('max_quantity')
    if isinstance(own, (int, float)) and own > 0 and unit == (product or {}).get('storage_unit'):
        return float(own)
    return {'кг': settings['max_kg'], 'шт': settings['max_pcs'],
            'уп': settings['max_packs']}.get(unit)


def check_plausibility(line, product, settings):
    """Quantity above the realistic limit: a weight said without a unit that fits
    as grams is converted («пятьсот» -> 0.5 кг, with a note, no review);
    anything else above the limit goes to review. No limit — no check."""
    quantity, unit = line.get('quantity'), line.get('unit')
    if not settings['plausibility'] or quantity is None:
        return line
    limit = quantity_limit(product, unit, settings)
    if limit is None or quantity <= limit:
        return line
    grams = round(quantity / 1000, 3)
    if (unit == 'кг' and settings['grams_over_limit'] and line.get('unit_source') != 'speech'
            and quantity >= 100 and grams <= limit):
        line['quantity'] = grams
        line['auto_note'] = (f'Сказано «{quantity:g}», при реалистичном максимуме {limit:g} кг '
                             f'это граммы: {grams:g} кг')
        return line
    reason = f'Нереалистичное количество: {quantity:g} {unit}, реалистичный максимум {limit:g} {unit}'
    line['needs_review'] = True
    line['review_reason'] = '; '.join(filter(None, [line.get('review_reason'), reason]))
    return line
