"""Voice order parsing v3: split by spoken quantities -> shortlist -> checked choice.

Order: `order_segmenter.segment` cuts the transcript into «name + quantity [+ unit]";
`shortlist` finds catalog candidates; `lexical_decision` picks the only candidate
that fits everything the customer said; `decide` confirms a line automatically
only when every check passes, otherwise the line stays in the order with
needs_review=True and a reason. `decide` also accepts a choice from another
source (for example an LLM), and checks it the same way.

Measured on 20 recordings from local/ (experiments/voice-order-20260924/README.md).
"""
import math
import re

from catalog_matching import CatalogIndex, grams
from order_segmenter import apply_voice_dictionary, normalize, segment
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


def _word_strength(spoken, token):
    """1.0 for the same word (abbreviation, case ending, synonym), otherwise how
    similar the letters are: «отвенский» ~ «венский» 0.875."""
    from difflib import SequenceMatcher
    if len(token) >= 3 and spoken.startswith(token):
        return 1.0  # abbreviation: «охл» = «охлажденные»
    if _stem(spoken) == _stem(token):
        return 1.0
    for said, meant in SYNONYMS.items():
        if spoken.startswith(said) and (token == meant or token.startswith(meant)):
            return 1.0
    return SequenceMatcher(None, spoken, token).ratio()


def _word_match(spoken, token):
    return _word_strength(spoken, token) >= .8


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
               and not w[0].isdigit()
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


def _meaningful(spoken_name):
    from spoken_quantity import NUMBER_WORD
    return [w for w in normalize(spoken_name).split()
            if len(w) >= 3 and w not in STOP and w not in NUMBER_WORD and not SIZE_WORDS.match(w)
            and not w[0].isdigit() and not PACK_SPOKEN['газ'].match(w) and w != 'вакуум']


def match_quality(spoken_name, product_name):
    """How exactly the spoken words are found in the product name, 0..1: the mean
    of the best strength of every spoken word. Settles a conflict between two
    products that both fit a misheard word («сервел отвенский» — «Венский» 0.93
    vs a hypothetical «Невский» 0.85), never two that differ by an unspoken word."""
    tokens = normalize(product_name).split()
    words = _meaningful(spoken_name)
    if not words or not tokens:
        return 1.0
    return sum(max(_word_strength(w, t) for t in tokens) for w in words) / len(words)


QUALITY_MARGIN = .05


def plausible(item, candidates):
    """Candidates that cover every spoken word without an unspoken size variant;
    a product with an unspoken quoted variety name loses to one without; among
    the rest only those within QUALITY_MARGIN of the most exact match remain."""
    spoken_name = item.get('spoken_name', '')
    spoken = normalize(' '.join(str(item.get(k) or '') for k in ('spoken_name', 'source_text')))
    size_said = bool(SPOKEN_SIZE.search(spoken)) and not SPOKEN_WEIGHT.search(spoken)
    covering = [p for p in candidates if not name_covers(spoken_name, p['name'])]
    # portion/pieces variant only when said, unless the product exists only that way
    fit = [p for p in covering if is_portion(p) == size_said] or covering
    plain = [p for p in fit if not _unspoken_brand(spoken_name, p['name'])] or fit
    if len(plain) < 2:
        return plain
    quality = [match_quality(spoken_name, p['name']) for p in plain]
    top = max(quality)
    return [p for p, q in zip(plain, quality) if q >= top - QUALITY_MARGIN]


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


class FastCatalogIndex(CatalogIndex):
    """The same ranking as CatalogIndex.rank (frozen by the benchmark), computed
    faster for large catalogs: product vector norms are computed once, and the
    similarity of a spoken word to a catalog word is computed once per query
    instead of once per product."""

    def __init__(self, catalog):
        super().__init__(catalog)
        self.norms = [sum((v * self.idf.get(g, 1)) ** 2 for g, v in pg.items()) for pg in self.grams]
        self.words = [t.split() for t in self.texts]

    def rank(self, query, limit=8):
        from difflib import SequenceMatcher
        from catalog_matching import normalize as catalog_normalize
        q = catalog_normalize(query)
        qg = grams(q)
        qnorm = sum((v * self.idf.get(g, 1)) ** 2 for g, v in qg.items())
        words = [w for w in q.split() if len(w) > 2]
        ratio = {}

        def similar(w, p):
            if (w, p) not in ratio:
                ratio[w, p] = SequenceMatcher(None, w, p).ratio()
            return ratio[w, p]

        def score(index):
            pg = self.grams[index]
            dot = sum(v * pg.get(g, 0) * self.idf.get(g, 1) ** 2 for g, v in qg.items())
            denom = math.sqrt(qnorm * self.norms[index])
            cosine = dot / denom if denom else 0
            overlap = sum(max((similar(w, p) for p in self.words[index]), default=0)
                          for w in words) / max(1, len(words))
            return .7 * cosine + .3 * overlap
        return sorted(range(len(self.catalog)), key=score, reverse=True)[:limit]


SIZE_IN_NAME = re.compile(r'(\d+(?:[.,]\d+)?)\s*(гр|г|кг)(?![а-я])')
PORTION_IN_NAME = re.compile(r'\(\s*(0[.,]\d+)\s*\)')


def name_sizes(name):
    """Pack sizes written in a product name, in grams: «250 гр» -> 250,
    «2.500 гр» -> 2500, «( 0.300 )» -> 300, «1.5 кг» -> 1500."""
    sizes = set()
    for number, unit in SIZE_IN_NAME.findall(str(name or '').lower()):
        value = float(number.replace(',', '.'))
        if unit == 'кг':
            value *= 1000
        elif re.fullmatch(r'\d+[.,]\d{3}', number):
            value *= 1000  # «2.500 гр» is 2500 g written with a thousands point
        sizes.add(round(value))
    for number in PORTION_IN_NAME.findall(str(name or '')):
        sizes.add(round(float(number.replace(',', '.')) * 1000))
    return sizes


def size_from_name(line, item, candidates):
    """«зельц говяжий двести пятьдесят» with «Зельц Говяжий 250 гр» in the catalog:
    250 is the pack size from the name, not 250 pieces. The number picks the
    product among those that fit the spoken words; the quantity is unknown."""
    quantity = line.get('quantity')
    if quantity is None or line.get('unit_source') == 'speech' and line.get('unit') != 'кг':
        return line
    # every candidate the spoken words fit, portions included: the number is what names the size
    fitting = [p for p in candidates if not name_covers(item.get('spoken_name', ''), p['name'])]
    matched = []
    for p in fitting:
        sizes = name_sizes(p['name'])
        # a whole number of grams (250, 300, 2500) or a portion «ноль триста» for a piece product
        if (quantity >= 100 and round(quantity) == quantity and round(quantity) in sizes) or (
                0 < quantity < 1 and p.get('storage_unit') == 'шт' and round(quantity * 1000) in sizes):
            matched.append(p)
    if not matched:
        return line
    current = next((p for p in matched if p['id'] == line.get('nomenclature_id')), None)
    product = current or (matched[0] if len(matched) == 1 else None)
    reasons = [r for r in line['review_reason'].split('; ')
               if r and not r.startswith(('Подходит и другой товар', 'Выбрана фасовка', 'Уточните количество'))]
    if product:
        line.update(name=product['name'], nomenclature_id=product['id'],
                    unit=product.get('storage_unit'), unit_source='catalog')
    else:
        reasons.append('Подходят несколько товаров: ' + '; '.join(p['name'].strip() for p in matched[:3]))
    reasons.append(f'Уточните количество: «{quantity:g}» — это фасовка из названия товара')
    line.update(quantity=None, needs_review=True, review_reason='; '.join(reasons))
    return line


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


# «написали 4, просят исправить на 6», «уберите», «вместо …» — это правка прошлого
# заказа, а не новый заказ: такие сообщения целиком отдаём менеджеру.
CORRECTION = re.compile(r'\b(исправ\w*|ошибл\w*|ошибк\w*|отмен\w*|убер\w*|убрать|замен\w*|вместо|не надо)\b')


def parse_order(transcript, catalog_rows, limit=8, dictionary_entries=None, settings=None):
    """Transcript + branch catalog -> order lines (dicts), no network calls.
    settings: branch options (order_settings.py); None means defaults."""
    from order_settings import check_plausibility, clean
    settings = clean(settings)
    catalog = usable_catalog(catalog_rows)
    by_id = {p['id']: p for p in catalog}
    transcript = apply_voice_dictionary(transcript, dictionary_entries, catalog)
    index = FastCatalogIndex(catalog)
    lines, previous = [], None
    for item in segment(transcript, catalog, corrections=settings['corrections']):
        candidates = shortlist(index, item, limit, previous)
        line = decide(item, candidates, lexical_decision(item, candidates))
        if settings['size_in_name']:
            line = size_from_name(line, item, candidates)
        lines.append(check_plausibility(line, by_id.get(line['nomenclature_id']), settings))
        previous = item['spoken_name']
    if CORRECTION.search(normalize(transcript)):
        for line in lines:
            line['needs_review'] = True
            line['review_reason'] = '; '.join(filter(None, [
                'Похоже на исправление прошлого заказа («исправить», «убрать», «вместо»)',
                line['review_reason']]))
    return lines
