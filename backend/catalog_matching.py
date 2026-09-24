"""Small-catalog retrieval and guarded selection for voice orders."""
import math
import re
from collections import Counter
from difflib import SequenceMatcher


def normalize(text):
    text = str(text or '').lower().replace('ё', 'е')
    for before, after in [('бачок', 'бочок'), ('бужиналь', 'буженаль'),
                          ('индийк', 'индейк'), ('в вакууме', 'в/у')]:
        text = text.replace(before, after)
    return ' '.join(re.findall(r'[а-яa-z0-9]+', text))


def grams(text):
    text = normalize(text)
    return Counter(text[i:i + 3] for i in range(max(0, len(text) - 2)))


class CatalogIndex:
    def __init__(self, catalog):
        self.catalog = catalog
        self.texts = [normalize(p['name']) for p in catalog]
        self.grams = [grams(t) for t in self.texts]
        frequency = Counter(g for row in self.grams for g in row)
        self.idf = {g: math.log(1 + len(catalog) / count) for g, count in frequency.items()}

    def rank(self, query, limit=8):
        q = normalize(query)
        qg = grams(q)
        def score(index):
            pg = self.grams[index]
            dot = sum(v * pg.get(g, 0) * self.idf.get(g, 1) ** 2 for g, v in qg.items())
            denom = math.sqrt(sum((v*self.idf.get(g, 1))**2 for g,v in qg.items())
                              * sum((v*self.idf.get(g, 1))**2 for g,v in pg.items()))
            cosine = dot / denom if denom else 0
            words = [w for w in q.split() if len(w) > 2]
            product_words = self.texts[index].split()
            overlap = sum(max((SequenceMatcher(None, w, p).ratio() for p in product_words), default=0)
                          for w in words) / max(1, len(words))
            return .7 * cosine + .3 * overlap
        return sorted(range(len(self.catalog)), key=score, reverse=True)[:limit]


def hybrid_rank(lexical, dense, limit=8):
    """Reciprocal rank fusion, with equal weight and fixed k=20."""
    scores = Counter()
    for ranking in (lexical, dense):
        for i, candidate in enumerate(ranking):
            scores[candidate] += 1 / (20 + i + 1)
    return [index for index, _ in scores.most_common(limit)]


def is_metadata(item):
    text = normalize(item.get('source_text') or item.get('spoken_name'))
    return bool(re.search(r'\b(прайс|процентный|машина|маршрут|адрес)\b', text)) and not re.search(
        r'\b(сосиск\w*|колбас\w*|рулет\w*|пельмен\w*|мяс\w*|ветчин\w*|грудинк\w*|купат\w*)\b', text)


def competing_products(item, candidates):
    words = [w for w in normalize(item.get('spoken_name')).split()
             if w not in {'из', 'мяса', 'с', 'со', 'в', 'на', 'по'} and (len(w) > 2 or w in {'кд', 'цб'})]
    if len(words) < 2:
        return []
    matches = []
    for product in candidates:
        tokens = normalize(product['name']).split()
        if all(any(w == t or (min(len(w), len(t)) >= 4 and
                   SequenceMatcher(None, w, t).ratio() >= .8) for t in tokens) for w in words):
            matches.append(product)
    return matches


def guarded_selection(item, candidates, decision):
    """Never turn a valid-but-wrong ID into an apparently valid order."""
    reasons = []
    choice = decision.get('choice')
    product = None
    if isinstance(choice, int) and not isinstance(choice, bool) and 1 <= choice <= len(candidates):
        product = candidates[choice - 1]
        if normalize(decision.get('name')) != normalize(product['name']):
            product = None
            reasons.append('Выбранный номер и название товара не совпадают')
    competing = competing_products(item, candidates)
    if product and len(competing) > 1:
        product = None
        reasons.append('Название подходит к нескольким вариантам упаковки или фасовки')
    if product is None:
        reasons.append('Требуется выбрать номенклатуру')
    if decision.get('needs_review') is not False:
        reasons.append(str(decision.get('reason') or 'Неоднозначный товар'))
    quantity = item.get('quantity')
    if (isinstance(quantity, bool) or not isinstance(quantity, (int, float))
            or quantity <= 0 or (isinstance(quantity, float) and not math.isfinite(quantity))):
        quantity = None
        reasons.append('Уточните количество')
    # Do not trust a model's invented unit; it must occur in the evidence quote.
    source = normalize(item.get('source_text'))
    unit = ('кг' if re.search(r'\b(кг|кило|килограмм\w*)\b', source) else
            'шт' if re.search(r'\b(шт|штук\w*)\b', source) else None)
    unit_source = 'speech' if unit else 'unknown'
    if not unit and product:
        unit = product.get('storage_unit') or product.get('report_unit')
        unit_source = 'catalog' if unit else 'unknown'
    if not unit:
        reasons.append('Уточните единицу измерения')
    if item.get('needs_review'):
        reasons.append(str(item.get('review_reason') or 'Неоднозначная позиция в речи'))
    return {
        'name': product['name'] if product else item.get('spoken_name', ''),
        'nomenclature_id': product['id'] if product else None,
        'quantity': quantity, 'unit': unit, 'unit_source': unit_source,
        'source_text': item.get('source_text'), 'notes': item.get('comments', ''),
        'needs_review': bool(reasons), 'review_reason': '; '.join(reasons),
        'candidate_ids': [p['id'] for p in candidates],
    }
