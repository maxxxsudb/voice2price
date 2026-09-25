"""Deterministic parsing of spoken Russian quantities in voice orders.

Used as an independent check of LLM output: a quantity the model returns must be
one of the quantities actually spoken in its source quote, otherwise the line
goes to review. Also gives a transcript with numbers marked for the prompt.

Examples: «кило двести» -> 1.2 кг, «два шестьсот» -> 2.6, «ноль восемь» -> 0.8,
«три с половиной» -> 3.5, «полтора» -> 1.5, «четыре штуки» -> 4 шт,
«килограмм» after a product -> 1 кг, «триста грамм» -> 0.3 кг.
"""
import re

UNITS = {
    'ноль': 0, 'один': 1, 'одна': 1, 'одно': 1, 'одну': 1, 'два': 2, 'две': 2,
    'три': 3, 'четыре': 4, 'пять': 5, 'шесть': 6, 'семь': 7, 'восемь': 8,
    'девять': 9,
}
TEENS = {
    'десять': 10, 'одиннадцать': 11, 'двенадцать': 12, 'тринадцать': 13,
    'четырнадцать': 14, 'пятнадцать': 15, 'шестнадцать': 16,
    'семнадцать': 17, 'восемнадцать': 18, 'девятнадцать': 19,
}
TENS = {
    'двадцать': 20, 'тридцать': 30, 'сорок': 40, 'пятьдесят': 50,
    'шестьдесят': 60, 'семьдесят': 70, 'восемьдесят': 80, 'девяносто': 90,
}
HUNDREDS = {
    'сто': 100, 'двести': 200, 'триста': 300, 'четыреста': 400,
    'пятьсот': 500, 'шестьсот': 600, 'семьсот': 700, 'восемьсот': 800,
    'девятьсот': 900,
}
HALF = {'полтора': 1.5, 'полторы': 1.5}
PAIR = {'пара': 2, 'пару': 2, 'пары': 2, 'парочка': 2, 'парочку': 2}
THOUSAND = re.compile(r'^тысяч\w*$')
DOZEN = {'десяток', 'десятка', 'десятков'}
KG = re.compile(r'^(кг|кило|килограмм\w*|кил)$')
GRAM = re.compile(r'^(г|гр|грамм\w*)$')
PCS = re.compile(r'^(шт|штук\w*|штуч\w*)$')
# Counted packages: the number is a count of packs/sticks, not kilograms.
SIZE_UNIT = re.compile(r'^(мл|мг|л|см|мм|процент\w*|%)$')
PACK = re.compile(r'^(пач\w*|упаков\w*|упак|короб\w*|палк\w*|палоч\w*|батон\w*|'
                  r'лот\w*|ящик\w*|банк\w*|пакет\w*|блок\w*|булк\w*|рулон\w*)$')
NUMBER_WORD = (set(UNITS) | set(TEENS) | set(TENS) | set(HUNDREDS) | set(HALF) | set(PAIR)
               | DOZEN | {'тысяча', 'тысячу'})


def tokens(text):
    text = str(text or '').lower().replace('ё', 'е')
    text = re.sub(r'(?<=\d),(?=\d)', '.', text)
    return re.findall(r'\d+(?:\.\d+)?|[а-яa-z]+', text)


def _integer(words, i):
    """Read one integer written in words or digits; return (value, next).
    «тысяча двести» = 1200, «две тысячи» = 2000, «два десятка» = 20."""
    value, j = _below_thousand(words, i)
    if j < len(words) and THOUSAND.match(words[j]):
        rest, k = _below_thousand(words, j + 1)
        return (1 if value is None else value) * 1000 + (rest or 0), k
    if value is not None and j < len(words) and words[j] in DOZEN:
        return value * 10, j + 1
    if value is None and i < len(words) and words[i] in DOZEN:
        return 10, i + 1
    return value, j


def _below_thousand(words, i):
    """Read one integer 0..999 written in words or digits; return (value, next)."""
    if i >= len(words):
        return None, i
    w = words[i]
    if re.fullmatch(r'\d+(?:\.\d+)?', w):
        return float(w) if '.' in w else int(w), i + 1
    if w in PAIR:
        return PAIR[w], i + 1
    value, start = 0, i
    if w in HUNDREDS:
        value += HUNDREDS[w]; i += 1
        w = words[i] if i < len(words) else ''
    if w in TEENS:
        return value + TEENS[w], i + 1
    if w in TENS:
        value += TENS[w]; i += 1
        w = words[i] if i < len(words) else ''
    if w in UNITS and not (value and w == 'ноль'):
        value += UNITS[w]; i += 1
    return (value, i) if i > start else (None, start)


def _hundreds_only(words, i):
    """«двести», «шестьсот», «двести пятьдесят» -> grams as a fraction of kg."""
    if i < len(words) and words[i] in HUNDREDS:
        value, j = _integer(words, i)
        return value / 1000, j
    return None, i


def parse_at(words, i):
    """Try to read a quantity starting at words[i].

    Returns dict(value, unit, start, end, text) or None. unit is 'кг', 'шт',
    'уп' (package-like count) or None when not spoken.
    """
    start = i
    w = words[i]
    value = None
    if w in HALF:
        value, i = HALF[w], i + 1
        if i < len(words) and THOUSAND.match(words[i]):
            value, i = 1500, i + 1  # «полторы тысячи»
    elif w in ('пол', 'полкило', 'полкилограмма'):
        if w != 'пол' or (i + 1 < len(words) and KG.match(words[i + 1])):
            value, i = 0.5, i + 1
            if w == 'пол':
                i += 1
            return _finish(words, start, i, value, 'кг')
        return None
    elif KG.match(w):
        # «кило двести» = 1.2 кг; a bare «кило/килограмм» = 1 кг.
        grams, j = _hundreds_only(words, i + 1)
        if grams is not None:
            return _finish(words, start, j, round(1 + grams, 3), 'кг', unit_read=True)
        return _finish(words, start, i + 1, 1, 'кг', unit_read=True)
    else:
        value, i = _integer(words, i)
        if value is None:
            return None
        if value == 0 and i < len(words):
            # «ноль восемь» = 0.8, «ноль двадцать пять» = 0.25, «ноль три» = 0.3
            frac, j = _integer(words, i)
            if frac is not None and frac > 0:
                digits = len(str(frac)) if frac >= 10 else 1
                return _finish(words, start, j, round(frac / 10 ** digits, 3), None)
            return None  # «ноль процентный» is not a quantity
        if i < len(words) and words[i] == 'с' and i + 1 < len(words) and words[i + 1].startswith('половин'):
            value, i = value + 0.5, i + 2
        elif i < len(words) and KG.match(words[i]):
            # «два кило пятьсот» = 2.5
            grams, j = _hundreds_only(words, i + 1)
            if grams is not None:
                return _finish(words, start, j, round(value + grams, 3), 'кг', unit_read=True)
        else:
            grams, j = _hundreds_only(words, i)
            if grams is not None and 1 <= value <= 20 and value == int(value):
                # «два шестьсот» = 2.6 (kg + grams)
                return _finish(words, start, j, round(value + grams, 3), None)
    return _finish(words, start, i, value, None)


def _finish(words, start, end, value, unit, unit_read=False):
    if not unit_read and end < len(words):
        w = words[end]
        if SIZE_UNIT.match(w):
            return None  # «шприц 5 мл», «жирность 20 процентов» — part of the name
        if KG.match(w):
            unit, end = 'кг', end + 1
        elif GRAM.match(w):
            unit, end, value = 'кг', end + 1, round(value / 1000, 3)
        elif PCS.match(w):
            unit, end = 'шт', end + 1
        elif PACK.match(w):
            unit, end = 'уп', end + 1
    return {'value': value, 'unit': unit, 'start': start, 'end': end,
            'text': ' '.join(words[start:end])}


def join_decimal(words, q):
    """«два и семь» = 2.7, «один и шесть» = 1.6 (kilograms and hundreds of grams);
    «три целых две десятых» = 3.2."""
    j = q['end']
    if j < len(words) and words[j].startswith('цел') and isinstance(q['value'], int):
        frac = parse_at(words, j + 1) if j + 1 < len(words) else None
        if frac and isinstance(frac['value'], int) and frac['end'] < len(words):
            scale = {'десят': 10, 'сотых': 100, 'сотая': 100, 'тысяч': 1000}
            den = next((v for k, v in scale.items() if words[frac['end']].startswith(k)), None)
            if den:
                end = frac['end'] + 1
                unit = None
                if end < len(words) and KG.match(words[end]):
                    unit, end = 'кг', end + 1
                return dict(q, value=round(q['value'] + frac['value'] / den, 3), unit=unit or q['unit'],
                            end=end, text=' '.join(words[q['start']:end]))
    if (q['unit'] is None and j + 1 < len(words) and words[j] == 'и'
            and isinstance(q['value'], int) and q['value'] < 10):
        nxt = parse_at(words, j + 1)
        if nxt and isinstance(nxt['value'], int) and 0 < nxt['value'] < 10 and nxt['unit'] is None:
            return dict(q, value=round(q['value'] + nxt['value'] / 10, 3), end=nxt['end'],
                        text=' '.join(words[q['start']:nxt['end']]))
    return q


def find_quantities(text):
    """All quantity phrases in order of appearance."""
    words = tokens(text)
    found, i = [], 0
    while i < len(words):
        q = parse_at(words, i)
        if q:
            q = join_decimal(words, q)
            found.append(q)
            i = q['end']
        else:
            i += 1
    return found


def spoken_values(text):
    return [q['value'] for q in find_quantities(text)]


def quantity_is_spoken(quantity, source_text, tolerance=1e-6):
    """True when the model's quantity equals a quantity spoken in the quote."""
    if quantity is None:
        return True
    return any(abs(float(quantity) - v) <= tolerance for v in spoken_values(source_text))
