"""Who is ordering: the client named at the start of a voice order
(«Мустафино, Лениногорск, бочок индейки килограмм»), matched against the
branch client list and the client pronunciation variants of the dictionary.

A client is confirmed only when every word of its name was said and no other
client matches the same words; otherwise the manager chooses (candidates listed).
"""
import re

from order_pipeline import _word_match
from order_segmenter import _known, catalog_vocabulary, normalize

LEGAL_FORM = re.compile(r'\b(ооо|оао|зао|пао|ао|ип|чп|тоо|индивидуальный|предприниматель)\b')
HEAD_WORDS = 15


def client_tokens(name):
    return [w for w in LEGAL_FORM.sub(' ', normalize(name)).split() if len(w) >= 3 and not w[0].isdigit()]


def _aliases(client, dictionary_entries):
    names = [client.get('name'), client.get('public_name')]
    for entry in dictionary_entries or []:
        if entry.get('category') == 'client' and (
                entry.get('item_id') == client.get('id') or entry.get('original') == client.get('name')):
            names += [v.get('variant') for v in entry.get('variants') or []]
    seen, result = set(), []
    for name in names:
        tokens = client_tokens(name)
        if tokens and tuple(tokens) not in seen:
            seen.add(tuple(tokens))
            result.append(tokens)
    return result


def _matches(token, said):
    return any(w[:2] == token[:2] and _word_match(w, token) for w in said)


def head_words(transcript, catalog):
    """Words before the first product word: where the client and address are said."""
    vocab = catalog_vocabulary(catalog or [])
    head = []
    for w in normalize(transcript).split()[:HEAD_WORDS]:
        if _known(w, vocab):
            break
        head.append(w)
    return head


def detect_client(transcript, clients, catalog=None, dictionary_entries=None):
    """Return {client_id, name, said, needs_review, review_reason, candidates} or
    None when the branch has no client list."""
    if not clients:
        return None
    said = [w for w in head_words(transcript, catalog) if len(w) >= 3]
    scored = []
    for client in clients:
        best = None
        for tokens in _aliases(client, dictionary_entries):
            matched = [t for t in tokens if _matches(t, said)]
            if not matched:
                continue
            score = (len(matched) / len(tokens), len(matched), sum(map(len, matched)))
            if best is None or score > best[0]:
                best = (score, matched)
        if best:
            scored.append((best[0], best[1], client))
    scored.sort(key=lambda row: row[0], reverse=True)
    candidates = [{'id': str(c['id']), 'name': c['name']} for _, _, c in scored[:3]]
    if not scored:
        return {'client_id': None, 'name': None, 'said': ' '.join(said), 'needs_review': True,
                'review_reason': 'Клиент не назван или не найден в справочнике клиентов',
                'candidates': []}
    (ratio, count, _), matched, client = scored[0]
    # another client that the same words fit at least as well
    rivals = [c for score, _, c in scored[1:] if score[1] >= count]
    reasons = []
    if ratio < 1:
        reasons.append('Названа только часть имени клиента: ' + ', '.join(matched))
    if rivals:
        reasons.append('Подходят несколько клиентов: ' + '; '.join(c['name'] for c in rivals[:3]))
    return {'client_id': str(client['id']), 'name': client['name'], 'said': ' '.join(matched),
            'needs_review': bool(reasons), 'review_reason': '; '.join(reasons),
            'candidates': candidates}
