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


def normalize(text):
    text = str(text or '').lower().replace('ё', 'е')
    for before, after in SPEECH_ALIASES:
        text = text.replace(before, after)
    return _catalog_normalize(text)


FILLER = {'так', 'все', 'всё', 'е', 'э', 'ну', 'вот', 'ип', 'ооо', 'добавить', 'еще', 'ещё',
          'и', 'а', 'пожалуйста', 'спасибо', 'короче', 'значит', 'которая', 'который', 'которые'}
COMMENT = re.compile(r'^(комментари\w*|только|строго|самы\w|обязательно)$')


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


def segment(transcript, catalog):
    vocab = catalog_vocabulary(catalog)
    heads = head_nouns(catalog)
    words = [w for w in tokens(normalize(transcript))]
    items, name, i = [], [], 0
    comment_mode = False
    segments_seen = 0
    pack = None
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
            if comment_mode and items:
                comment, new_line = _split_comment(kept, items, heads)
                items[-1]['comments'] = (items[-1]['comments'] + ' ' +
                                         ' '.join(comment + ([] if new_line else [q['text']]))).strip()
                if new_line:
                    items.append({'spoken_name': ' '.join(new_line), 'quantity': q['value'],
                                  'explicit_unit': q['unit'], 'comments': '',
                                  'source_text': ' '.join(new_line + [q['text']])})
            elif kept and (segments_seen > 0 or any(_known(x, vocab) for x in kept)):
                if segments_seen == 0:
                    # client/address glued to the first product: drop words before
                    # the first catalog word
                    k = next((n for n, x in enumerate(kept) if _known(x, vocab)), 0)
                    kept = kept[k:]
                item = {'spoken_name': ' '.join(kept), 'quantity': q['value'],
                        'explicit_unit': q['unit'], 'source_text': ' '.join(name + [q['text']]),
                        'comments': ''}
                if pack is not None and abs(pack - q['value']) < 1e-9:
                    item['needs_review'] = True
                    item['review_reason'] = f'Сказано «по {pack} … {pack}»: фасовка или количество?'
                items.append(item)
            elif items and not kept and q['unit'] and items[-1]['explicit_unit'] is None \
                    and items[-1]['quantity'] is not None \
                    and abs(items[-1]['quantity'] - q['value']) < 1e-9:
                items[-1]['explicit_unit'] = q['unit']  # «пять ... пять килограмм» repeat
            if kept:
                segments_seen += 1
            pack = None
            name, i = [], q['end']
            # a comment lasts until a new product is named after it
            comment_mode = comment_mode and not new_line
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
        items.append({'spoken_name': ' '.join(kept), 'quantity': None, 'explicit_unit': None,
                      'source_text': ' '.join(name), 'comments': ''})
    _route_comments(items, heads)
    return items


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
