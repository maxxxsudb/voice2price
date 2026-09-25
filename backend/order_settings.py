"""Order parsing options of one branch (branch manager): each check can be turned off.

Stored as JSON in employees.order_settings; missing keys take the defaults below,
so old records and new options work without a migration.
"""
import json

DEFAULTS = {
    # «два кило, точнее три» — replace the previous quantity instead of a new line
    'corrections': True,
    # Realistic quantity: more than the limit goes to review
    'plausibility': True,
    'max_kg': 50.0,       # default limit for goods in kg (a product's own limit wins)
    'max_pcs': 300.0,     # default limit for goods in pieces
    'max_packs': 100.0,   # default limit for packs/boxes
    'suggest_grams': True,  # «сосиски пятьсот» at 5 kg limit -> «возможно, 0.5 кг»
    # Client from the start of the message, by the branch client list
    'detect_client': True,
    # Consecutive voice messages of one client -> one order
    'merge_messages': True,
    'merge_window_min': 15.0,
}

BOOLEAN = {k for k, v in DEFAULTS.items() if isinstance(v, bool)}
NUMBER = {k for k, v in DEFAULTS.items() if isinstance(v, float)}


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
        value = raw.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 < value < 1e6:
            result[key] = float(value)
    return result


def dumps(settings):
    return json.dumps(clean(settings), ensure_ascii=False)


def quantity_limit(product, unit, settings):
    """Limit for one line: the product's own max_quantity, else the branch default by unit."""
    own = (product or {}).get('max_quantity')
    if isinstance(own, (int, float)) and own > 0:
        return float(own)
    return {'кг': settings['max_kg'], 'шт': settings['max_pcs'],
            'уп': settings['max_packs']}.get(unit)


def check_plausibility(line, product, settings):
    """Mark an unrealistic quantity for review; never change the quantity itself."""
    quantity, unit = line.get('quantity'), line.get('unit')
    if not settings['plausibility'] or quantity is None:
        return line
    limit = quantity_limit(product, unit, settings)
    if limit is None or quantity <= limit:
        return line
    shown = f'{limit:g} {unit}'
    reason = f'Нереалистичное количество: {quantity:g} {unit}, обычно не больше {shown}'
    if unit == 'кг' and settings['suggest_grams'] and quantity >= 100 and quantity / 1000 <= limit:
        grams = round(quantity / 1000, 3)
        reason += f' — возможно, сказаны граммы: {grams:g} кг'
        line['suggested_quantity'] = grams
    line['needs_review'] = True
    line['review_reason'] = '; '.join(filter(None, [line.get('review_reason'), reason]))
    return line
