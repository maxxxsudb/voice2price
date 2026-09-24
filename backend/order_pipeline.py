"""Voice order parsing v3: split by spoken quantities -> shortlist -> checked choice.

Order: `order_segmenter.segment` cuts the transcript into «name + quantity [+ unit]";
`shortlist` finds catalog candidates; `lexical_decision` picks the only candidate
that fits everything the customer said; `decide` confirms a line automatically
only when every check passes, otherwise the line stays in the order with
needs_review=True and a reason. `decide` also accepts a choice from another
source (for example an LLM), and checks it the same way.

Measured on 20 recordings from local/ (see VOICE_ORDER_EVALUATION.md).
"""
import math
import re

from catalog_matching import CatalogIndex
from order_segmenter import normalize, segment
from spoken_quantity import quantity_is_spoken

# Size/portion markers: a product carrying one of these is chosen only when the
# customer said it (e.g. «половинка», «0.300», «порционный», «штучный», «мини»).
SIZE_MARKERS = re.compile(r'половинк|\(\s*0\.\d+|\b0\.\d{3}\b|\bпорц|штучн|\bмини\b|\(шт\)|\bшт\s*\)|(?<![\d.])\d{2,3}\s?гр')
SPOKEN_SIZE = re.compile(r'половинк|порци|штучн|мини|\bпо ноль|\bпо 0')
SPOKEN_WEIGHT = re.compile(r'весов')


def usable_catalog(rows):
    """Drop services and items marked «НЕ БРАТЬ» from what may be chosen."""
    out = []
    for p in rows:
        name = p.get('name') or ''
        if re.search(r'не\s*брать|услуг|обслуживан|программ|аренд|проживан', name, re.I):
            continue
        if (p.get('nomenclature_type') or 'Товар') != 'Товар':
            continue
        if (p.get('storage_unit') or 'кг') in ('руб', 'м2'):
            continue
        out.append(p)
    return out


STOP = {'из', 'мяса', 'мясо', 'с', 'со', 'в', 'на', 'по', 'и', 'у', 'для', 'ноль', 'как', 'про'}
PACK_SPOKEN = {'газ': re.compile(r'\bгаз'), 'в/у': re.compile(r'\bв у\b|вакуум')}
SIZE_WORDS = re.compile(r'^(весов\w*|порци\w*|штучн\w*|мини|половин\w*|большо\w*|больш\w*)$')


ENDINGS = re.compile(r'(ого|его|ому|ему|ыми|ими|ая|яя|ое|ее|ые|ие|ый|ий|ой|ую|юю|ых|их|ам|ям|ах|ях|ом|ем|а|я|о|е|ы|и|у|ю|ь)$')
# spoken stem -> catalog token stem (kind of meat said as an adjective)
SYNONYMS = {'курин': 'цб', 'куриц': 'цб', 'утин': 'утк', 'гусин': 'гус', 'индюш': 'индейк',
            'свин': 'свин', 'говяж': 'говяж'}


def _stem(word):
    return ENDINGS.sub('', word) if len(word) > 4 else word


def _word_match(spoken, token):
    from difflib import SequenceMatcher
    if len(token) >= 3 and spoken.startswith(token):
        return True  # abbreviation: «охл» = «охлажденные»
    if _stem(spoken) == _stem(token):
        return True
    for said, meant in SYNONYMS.items():
        if spoken.startswith(said) and (token == meant or token.startswith(meant)):
            return True
    return SequenceMatcher(None, spoken, token).ratio() >= .8


ABBREVIATIONS = {'ск': r'\bс к\b|сырокопч', 'пк': r'\bп к\b|полукопч', 'вк': r'\bв к\b|варено копч',
                 'кв': r'\bк в\b|копчено вар', 'цб': r'\bцб\b|ц б|цыпл', 'кд': r'\bкд\b'}


def name_covers(spoken_name, product_name):
    """Every meaningful spoken word must be found in the product name, and a
    spoken packaging (газ / вакуум) must be present in the product."""
    from spoken_quantity import NUMBER_WORD
    tokens = normalize(product_name).split()
    spoken = normalize(spoken_name)
    missing = [w for w in spoken.split()
               if len(w) >= 3 and w not in STOP and w not in NUMBER_WORD and not SIZE_WORDS.match(w)
               and not PACK_SPOKEN['газ'].match(w) and w != 'вакуум'
               and not any(_word_match(w, t) for t in tokens)]
    product = normalize(product_name)
    # «варено-копченая», «копченый» = к/в, в/к, с/к, п/к in the catalog
    smoked = re.search(r'\b[квсп] к\b|\bк в\b|копч', product)
    missing = [w for w in missing if not (smoked and re.match(r'(копч|варен)', w))]
    for w in spoken.split():
        if w in ABBREVIATIONS and not re.search(ABBREVIATIONS[w], product):
            missing.append(w)
    for word, rx in PACK_SPOKEN.items():
        if rx.search(spoken) and not rx.search(product):
            missing.append(word)
    return missing


def _unspoken_brand(spoken, product_name):
    """Quoted variety name («Филейный») the customer did not say."""
    brands = re.findall(r'"([^"]+)"', product_name)
    said = normalize(spoken).split()
    return any(w for b in brands for w in normalize(b).split()
               if len(w) >= 3 and not any(_word_match(x, w) for x in said))


def is_portion(product):
    return bool(SIZE_MARKERS.search(product['name'].lower())) or product.get('storage_unit') == 'шт'


def plausible(item, candidates):
    """Candidates that cover every spoken word without an unspoken size variant;
    a product with an unspoken quoted variety name loses to one without."""
    spoken_name = item.get('spoken_name', '')
    spoken = normalize(' '.join(str(item.get(k) or '') for k in ('spoken_name', 'source_text')))
    size_said = bool(SPOKEN_SIZE.search(spoken)) and not SPOKEN_WEIGHT.search(spoken)
    covering = [p for p in candidates if not name_covers(spoken_name, p['name'])]
    # portion/pieces variant only when said, unless the product exists only that way
    fit = [p for p in covering if is_portion(p) == size_said] or covering
    plain = [p for p in fit if not _unspoken_brand(spoken_name, p['name'])]
    return plain or fit


def decide(item, candidates, decision):
    """Turn a choice into an order line; never auto-confirm a doubtful one."""
    reasons = []
    spoken = normalize(' '.join(str(item.get(k) or '') for k in ('spoken_name', 'attributes', 'source_text')))
    product = None
    chosen = normalize(re.sub(r'\(ед\.?:[^)]*\)\s*$', '', str(decision.get('name') or '')))
    if chosen and chosen != 'нет':
        same = [p for p in candidates if normalize(p['name']) == chosen]
        if len(same) >= 1:
            product = same[0]
        else:
            reasons.append('Выбранный товар не найден среди кандидатов')
    if product is None:
        reasons.append('Выберите номенклатуру')
    else:
        missing = name_covers(item.get('spoken_name', ''), product['name'])
        if missing:
            reasons.append('Не совпадает со сказанным: ' + ', '.join(missing))
        # Portion/half/pieces variants only when said; «весовой»/nothing said -> not them.
        size_said = bool(SPOKEN_SIZE.search(spoken)) and not SPOKEN_WEIGHT.search(spoken)
        consistent = [p for p in candidates if not name_covers(item.get('spoken_name', ''), p['name'])
                      and is_portion(p) == size_said]
        if is_portion(product) != size_said and consistent:
            reasons.append('Клиент назвал штучный/порционный товар, выбран весовой' if size_said
                           else 'Выбрана фасовка/порция, о которой клиент не говорил')
        # Other candidates that fit everything the customer said equally well.
        rivals = [p for p in plausible(item, candidates) if p is not product]
        if rivals and product in plausible(item, candidates):
            names = '; '.join(p['name'].strip() for p in rivals[:3])
            reasons.append(f'Подходит и другой товар: {names}')
    if decision.get('needs_review') and decision.get('review_reason'):
        reasons.append(str(decision['review_reason']))
    elif decision.get('needs_review'):
        reasons.append('Выбор под сомнением')

    quantity = item.get('quantity')
    if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or not math.isfinite(quantity) or quantity <= 0:
        quantity = None
        reasons.append('Уточните количество')
    elif item.get('source_text') and not quantity_is_spoken(quantity, item['source_text']):
        reasons.append('Количество не найдено в цитате: проверьте')

    spoken_unit = item.get('explicit_unit') or item.get('unit')
    spoken_unit = spoken_unit if spoken_unit in ('кг', 'шт', 'уп') else None
    catalog_unit = (product or {}).get('storage_unit')
    unit, unit_source = None, 'unknown'
    if product:
        if spoken_unit in (None, catalog_unit):
            unit, unit_source = catalog_unit, ('speech' if spoken_unit else 'catalog')
        elif spoken_unit == 'уп' and catalog_unit == 'шт':
            unit, unit_source = 'шт', 'speech'
        else:
            unit, unit_source = spoken_unit, 'speech'
            reasons.append(f'Клиент сказал «{spoken_unit}», в справочнике «{catalog_unit}»: нужен пересчёт')
    else:
        unit = spoken_unit
    if unit is None:
        reasons.append('Уточните единицу измерения')

    if item.get('needs_review') and item.get('review_reason'):
        reasons.append(str(item['review_reason']))
    return {
        'name': product['name'] if product else item.get('spoken_name', ''),
        'nomenclature_id': product['id'] if product else None,
        'spoken_name': item.get('spoken_name', ''),
        'quantity': quantity, 'unit': unit, 'unit_source': unit_source,
        'source_text': item.get('source_text'), 'comments': item.get('comments', ''),
        'needs_review': bool(reasons), 'review_reason': '; '.join(dict.fromkeys(reasons)),
        'candidate_ids': [p['id'] for p in candidates],
    }


ADJECTIVE = re.compile(r'(ые|ие|ая|яя|ое|ий|ый|ой)$')


def lexical_decision(item, candidates):
    """No-LLM choice: the only candidate that fits everything said, otherwise
    the best-ranked one (decide() will then send it to review)."""
    fit = plausible(item, candidates)
    best = fit[0] if len(fit) == 1 else (candidates[0] if candidates else None)
    return {'name': best['name'] if best else None, 'needs_review': False}


def shortlist(index, item, limit=8, previous=None):
    """Candidates by name; a lone adjective («пикантные») also searches it
    together with the previous product («купаты куриные пикантные»)."""
    query = normalize(' '.join(str(item.get(k) or '') for k in ('spoken_name', 'attributes')))
    ranked = index.rank(query, limit=limit)
    if previous and len(query.split()) == 1 and ADJECTIVE.search(query):
        joined = index.rank(previous + ' ' + query, limit=limit)
        ranked = list(dict.fromkeys(joined[:limit // 2] + ranked))[:limit]
    return [index.catalog[i] for i in ranked]


def parse_order(transcript, catalog_rows, limit=8):
    """Transcript + employee catalog -> order lines (dicts), no network calls."""
    catalog = usable_catalog(catalog_rows)
    index = CatalogIndex(catalog)
    lines, previous = [], None
    for item in segment(transcript, catalog):
        candidates = shortlist(index, item, limit, previous)
        lines.append(decide(item, candidates, lexical_decision(item, candidates)))
        previous = item['spoken_name']
    return lines
