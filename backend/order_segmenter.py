"""Deterministic split of a voice order transcript into (name, quantity, unit).

Voice orders are a list «название количество [единица]». Spoken quantities are
the anchors: every quantity closes the product named since the previous one.
Words unknown to the catalog (client, address, small talk) are dropped.
The LLM is still used for choosing SKU; here we only cut the text.
"""
import re

from catalog_matching import normalize as _catalog_normalize
from spoken_quantity import tokens, parse_at, join_decimal, NUMBER_WORD

# Frequent SpeechKit mishearings (kept here so catalog_matching.py, frozen by the
# 2026-09-23 benchmark, stays unchanged).
SPEECH_ALIASES = [('студия', 'студень'), ('зель с ', 'зельц '), ('запеченый', 'запеченный')]


DECIMAL = re.compile(r'(\d+[.,]\d+)')


def normalize(text):
    """Catalog normalization that keeps decimal numbers whole: «1.5 кг», «0,3»
    must stay one number, not «1 5» (which read as 1 and lost 0.5)."""
    text = str(text or '').lower().replace('ё', 'е')
    for before, after in SPEECH_ALIASES:
        text = text.replace(before, after)
    parts = DECIMAL.split(text)
    return ' '.join(filter(None, (part.replace(',', '.') if n % 2 else _catalog_normalize(part)
                                  for n, part in enumerate(parts))))


def apply_voice_dictionary(text, entries, catalog):
    """Replace employee pronunciation variants with current catalog names."""
    catalog_names = {normalize(p.get('name')): normalize(p.get('name')) for p in catalog}
    variants = {}
    ambiguous = set()
    for entry in entries or []:
        get = entry.get if isinstance(entry, dict) else lambda key, default=None: getattr(entry, key, default)
        if get('category') != 'nomenclature':
            continue
        original = normalize(get('original'))
        canonical = catalog_names.get(original)
        if not canonical:
            continue
        for row in get('variants', []) or []:
            variant = normalize(row.get('variant') if isinstance(row, dict) else getattr(row, 'variant', ''))
            # Imported articles/codes are search keys, not pronunciation variants.
            if not re.search(r'[а-яa-z]', variant) or variant == canonical:
                continue
            if variant in variants and variants[variant] != canonical:
                ambiguous.add(variant)
            else:
                variants[variant] = canonical
    for variant in ambiguous:
        variants.pop(variant, None)
    normalized = normalize(text)
    if not variants:
        return normalized
    choices = '|'.join(re.escape(v) for v in sorted(variants, key=lambda v: (-len(v), v)))
    pattern = re.compile(rf'(?<![а-яa-z0-9])(?:{choices})(?![а-яa-z0-9])')
    return pattern.sub(lambda match: variants[match.group(0)], normalized)


FILLER = {'так', 'все', 'всё', 'е', 'э', 'ну', 'вот', 'ип', 'ооо', 'добавить', 'еще', 'ещё',
          'и', 'а', 'пожалуйста', 'спасибо', 'короче', 'значит', 'которая', 'который', 'которые'}
COMMENT = re.compile(r'^(комментари\w*|только|строго|самы\w|обязательно)$')
# «два кило, точнее три», «пять, нет, семь»: the customer corrects what was just said.
CORRECTION_WORDS = {'нет', 'точнее', 'вернее', 'поправка', 'поправлюсь', 'исправлюсь', 'ой'}


def catalog_vocabulary(catalog):
    vocab = set()
    for p in catalog:
        for w in normalize(p['name']).split():
            if len(w) >= 3 and not w.isdigit():
                vocab.add(w[:5])
    return vocab


def head_nouns(catalog):
    return {normalize(p['name']).split()[0][:5] for p in catalog if normalize(p['name']).split()}


def _split_comment(kept, items, heads):
    """In a comment, a product head noun not yet ordered starts a new line:
    «...только большой и заморозка зразы из индейки с сыром два»."""
    ordered = {w[:5] for it in items for w in it['spoken_name'].split()}
    for n in range(len(kept) - 1, -1, -1):
        w = kept[n]
        if len(w) >= 4 and w[:5] in heads and w[:5] not in ordered:
            return kept[:n], kept[n:]
    return kept, []


def _known(word, vocab):
    return len(word) >= 3 and word[:5] in vocab


def _stems(words):
    return {w[:4] for w in words if len(w) >= 3}


def _review(item, reason):
    item['needs_review'] = True
    item['review_reason'] = '; '.join(filter(None, [item.get('review_reason'), reason]))


def segment(transcript, catalog, corrections=True):
    """corrections=False turns off in-phrase corrections («два, нет, три»)."""
    vocab = catalog_vocabulary(catalog)
    heads = head_nouns(catalog)
    words = [w for w in tokens(normalize(transcript))]
    items, name, i = [], [], 0
    comment_mode = False
    segments_seen = 0
    pack = None
    correcting = None      # the word that started a correction of the previous line
    replaced_name = None   # «колбаса, нет, сардельки»: name words dropped by a correction
    leading = None         # quantity said before any product: «два пельмени»
    while i < len(words):
        w = words[i]
        # «по ноль пять» / «по 0.3» — pack weight, part of the name, not a quantity
        if w == 'по' and i + 1 < len(words):
            q = parse_at(words, i + 1)
            if q:
                name += words[i:q['end']]
                pack = q['value']
                i = q['end']
                continue
        q = parse_at(words, i) if (w in NUMBER_WORD or w[0].isdigit() or w.startswith('кило')
                                   or w in ('пол', 'полкило')) else None
        if q:
            q = join_decimal(words, q)
            kept = [x for x in name if x not in FILLER]
            new_line = []
            if correcting and items and (not kept or _stems(kept) <= _stems(items[-1]['spoken_name'].split())):
                # «колбаса два кило, точнее три» / «сосиски пять, нет, сосиски семь»
                prev = items[-1]
                prev['quantity'] = q['value']
                prev['explicit_unit'] = q['unit'] or prev['explicit_unit']
                prev['source_text'] = ' '.join([prev['source_text'], correcting] + name + [q['text']])
                prev['_qty_text'] = q['text']
                prev['corrected'] = True
            elif comment_mode and items:
                comment, new_line = _split_comment(kept, items, heads)
                items[-1]['comments'] = (items[-1]['comments'] + ' ' +
                                         ' '.join(comment + ([] if new_line else [q['text']]))).strip()
                if new_line:
                    items.append({'spoken_name': ' '.join(new_line), 'quantity': q['value'],
                                  'explicit_unit': q['unit'], 'comments': '', '_qty_text': q['text'],
                                  'source_text': ' '.join(new_line + [q['text']])})
            elif kept and (segments_seen > 0 or any(_known(x, vocab) for x in kept)):
                if segments_seen == 0:
                    # client/address glued to the first product: drop words before
                    # the first catalog word
                    k = next((n for n, x in enumerate(kept) if _known(x, vocab)), 0)
                    kept = kept[k:]
                item = {'spoken_name': ' '.join(kept), 'quantity': q['value'],
                        'explicit_unit': q['unit'], 'source_text': ' '.join(name + [q['text']]),
                        'comments': '', '_qty_text': q['text']}
                if pack is not None and abs(pack - q['value']) < 1e-9:
                    _review(item, f'Сказано «по {pack} … {pack}»: фасовка или количество?')
                if correcting and items:
                    # «сосиски пять, нет, колбаса семь»: replace or add? Ask.
                    reason = f'Клиент поправился («{correcting}»): заменить «{items[-1]["spoken_name"]}» или добавить?'
                    _review(items[-1], reason)
                    _review(item, reason)
                if replaced_name:
                    _review(item, f'Сказано «{replaced_name} …»: проверьте товар')
                items.append(item)
            elif items and not kept and q['unit'] and items[-1]['explicit_unit'] is None \
                    and items[-1]['quantity'] is not None \
                    and abs(items[-1]['quantity'] - q['value']) < 1e-9:
                items[-1]['explicit_unit'] = q['unit']  # «пять ... пять килограмм» repeat
            elif not items and not kept and leading is None:
                leading = q
            if kept:
                segments_seen += 1
            pack = None
            correcting = replaced_name = None
            name, i = [], q['end']
            # a comment lasts until a new product is named after it
            comment_mode = comment_mode and not new_line
            continue
        pair = ' '.join(words[i:i + 2])
        if corrections and items and not comment_mode and (w in CORRECTION_WORDS or pair == 'то есть'):
            correcting_word = pair if pair == 'то есть' else w
            kept = [x for x in name if x not in FILLER]
            if kept:
                # a name was being said and is corrected before its quantity
                replaced_name = ' '.join(kept + [correcting_word])
                name = []
            else:
                correcting = correcting_word
            i += 2 if pair == 'то есть' else 1
            continue
        if COMMENT.match(w):
            if w.startswith('комментари') or items:
                comment_mode = True
            if not w.startswith('комментари'):
                name.append(w)
            i += 1
            continue
        name.append(w)
        i += 1
    kept = [x for x in name if x not in FILLER]
    if comment_mode and items:
        items[-1]['comments'] = (items[-1]['comments'] + ' ' + ' '.join(kept)).strip()
    elif any(_known(x, vocab) for x in kept):
        if segments_seen == 0:
            kept = kept[next((n for n, x in enumerate(kept) if _known(x, vocab)), 0):]
        items.append({'spoken_name': ' '.join(kept), 'quantity': None, 'explicit_unit': None,
                      'source_text': ' '.join(name), 'comments': ''})
    if leading is not None and items:
        _quantity_first(items, leading)
    _route_comments(items, heads)
    for item in items:
        item.pop('_qty_text', None)
        item.pop('corrected', None)
    return items


KG_WORD = re.compile(r'^кило')


def _quantity_first(items, leading):
    """«два пельмени, три колбасы»: the customer says the quantity before the name.
    Recognized only when the message starts with a quantity and ends with a name
    without one; then every quantity belongs to the name that follows it."""
    # «борская килограмм, тушка утки»: a bare «кило/килограмм» closes the name
    # before it, so the order is name-first and nothing is shifted
    unit_led = any(KG_WORD.match(it.get('_qty_text', '')) for it in items[:-1])
    if items[-1]['quantity'] is not None or unit_led or any(it.get('corrected') for it in items):
        # a lone «килограмм» at the start is the tail of the previous message,
        # not a quantity of the first product here
        if not (KG_WORD.match(leading['text']) and leading['value'] == 1):
            _review(items[0], f'Перед названием сказано «{leading["text"]}»: проверьте количество')
        return
    quantities = [(leading['value'], leading['unit'], leading['text'])] + [
        (it['quantity'], it['explicit_unit'], it.get('_qty_text', '')) for it in items[:-1]]
    for item, (value, unit, text) in zip(items, quantities):
        item['quantity'], item['explicit_unit'] = value, unit
        item['source_text'] = ' '.join(filter(None, [text, item['spoken_name']]))


def _route_comments(items, heads):
    """«комментарий тушка утки строго две штуки ... рулет из индейки только большой»:
    each part that names an ordered product goes to that product."""
    stems = [{w[:4] for w in it['spoken_name'].split() if len(w) >= 3} for it in items]
    for idx, it in enumerate(items):
        if not it['comments']:
            continue
        words, parts = it['comments'].split(), []
        for n, w in enumerate(words):
            after_preposition = n > 0 and words[n - 1] in ('из', 'с', 'со', 'в', 'на', 'для')
            if not parts or (len(w) >= 4 and w[:5] in heads and not after_preposition):
                parts.append([w])
            else:
                parts[-1].append(w)
        it['comments'] = ''
        for part in parts:
            said = {w[:4] for w in part if len(w) >= 3}
            best = max(range(len(items)), key=lambda n: (len(said & stems[n]), n == idx))
            target = items[best] if len(said & stems[best]) >= 2 else it
            target['comments'] = (target['comments'] + ' ' + ' '.join(part)).strip()
