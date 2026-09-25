"""Who is ordering: the client named in a voice order («Мустафино, Лениногорск,
бочок индейки килограмм»), matched against the branch client list and the client
entries of the pronunciation dictionary.

A 1C client name looks like «Ногуманова Л.Л.(г.Лениногорск, ул.Степная,1)» or
«ИП Ногуманова Люция Людвиговна»; a company — «АПК КАМСКИЙ ООО». From it we
take the key words (the surname of a person, the name of a company) and the
supporting words (first name, patronymic, city, street). Short forms a manager
typed into the dictionary («магазин у дома») are the strongest evidence.

Score (confidence): dictionary short form 1.0; key words said 0.85, each
supporting word +0.05 (up to 0.97); only a city and a street 0.35–0.45. A client is
confirmed when the score is at least 0.85 and no other client is within 0.05 —
so a second said word (the city) settles two clients with the same surname,
and two equal ones go to the manager with the candidates listed.
"""
import re
from difflib import SequenceMatcher

from order_segmenter import _known, catalog_vocabulary, normalize

LEGAL_FORM = {'ооо', 'оао', 'зао', 'пао', 'ао', 'ип', 'чп', 'тоо', 'гбу', 'со', 'пф',
              'индивидуальный', 'предприниматель', 'общество', 'ограниченной', 'ответственностью'}
# words of a company name that do not identify it on their own
GENERIC = {'магазин', 'торговая', 'торговый', 'фирма', 'компания', 'филиал', 'дом', 'группа'}
ADDRESS_WORDS = {'ул', 'улица', 'пр', 'кт', 'пркт', 'проспект', 'пер', 'переулок', 'д', 'дом', 'г',
                 'город', 'пос', 'поселок', 'село', 'мкр', 'район', 'рн', 'база', 'скл', 'склад',
                 'тц', 'стр', 'корп', 'кв'}
ADDRESS_START = re.compile(r'\(|\bг\.|\bул\.|\bпр\.|\bд\.\s*\d')
PERSON = re.compile(r'(^|\s)[А-ЯЁ]\.\s?[А-ЯЁ]\.|(^|[\s"])ИП(\s|$)')
# surname and adjective case endings: Нурыев/Нурыеву/Нурыевым, Мингулова/Мингуловой
ENDINGS = re.compile(r'(ыми|ими|ого|его|ому|ему|ой|ей|ою|ую|юю|ым|им|ом|ем|ая|яя|ое|ее|ые|ие|ый|ий|'
                     r'ых|их|ам|ям|ах|ях|а|я|у|ю|ы|и|е|о|ь)$')

HEAD_WORDS = 15
CONFIRM = .85        # key words of the client were said
MARGIN = .05         # the next client must be at least this much weaker
DICTIONARY = 1.0
KEY = .85
SUPPORT = .05
AUTO_MAX = .97


def _words(text, drop=()):
    return [w for w in normalize(text).split()
            if len(w) >= 3 and not w[0].isdigit() and w not in drop]


def _stem(word):
    return ENDINGS.sub('', word) if len(word) >= 6 else word


def word_matches(token, said):
    """A said word that is this name word, allowing case endings and typical
    speech-recognition slips («нуреевым» = «Нурыев», «мустафино» = «Мустафина»)."""
    for w in said:
        if w[:2] != token[:2]:
            continue
        if w == token or _stem(w) == _stem(token):
            return w
        if SequenceMatcher(None, _stem(w), _stem(token)).ratio() >= .82:
            return w
    return None


def _split_name(name):
    """«Ногуманова Л.Л.(г.Лениногорск, ул.Степная,1)» -> ('Ногуманова Л.Л.', 'г.Лениногорск, ул.Степная,1')."""
    text = str(name or '')
    match = ADDRESS_START.search(text)
    if not match or match.start() == 0:
        return text, ''
    return text[:match.start()], text[match.start():]


def client_profile(client, dictionary_entries=None):
    """How a client can be named: key word sets (any one is enough), supporting
    words and the short forms from the dictionary."""
    get = client.get if isinstance(client, dict) else lambda k, d=None: getattr(client, k, d)
    keys, support, address, short_forms = [], set(), set(), []
    for field in ('name', 'public_name'):
        identity, where = _split_name(get(field))
        words = _words(identity, LEGAL_FORM)
        address.update(_words(where, ADDRESS_WORDS))
        if not words:
            continue
        if PERSON.search(str(get(field) or '')):
            key = [words[0]]              # surname; name and patronymic support it
        else:
            key = [w for w in words if w not in GENERIC] or words
        support.update(w for w in words if w not in key)
        if key not in keys:
            keys.append(key)
    client_id = str(get('id') or '')
    for entry in dictionary_entries or []:
        entry_get = entry.get if isinstance(entry, dict) else lambda k, d=None: getattr(entry, k, d)
        if entry_get('category') != 'client':
            continue
        if str(entry_get('item_id') or '') != client_id and entry_get('original') != get('name'):
            continue
        for variant in entry_get('variants') or []:
            text = variant.get('variant') if isinstance(variant, dict) else getattr(variant, 'variant', '')
            words = _words(text, LEGAL_FORM)
            # imported 1C codes and the public name are not short forms
            if words and not (text == get('public_name') or text == get('code')) and words not in short_forms:
                short_forms.append(words)
    key_words = {w for k in keys for w in k}
    return {'keys': keys, 'support': sorted(support - key_words),
            'address': sorted(address - key_words), 'short_forms': short_forms}


def score_client(profile, said):
    """(score, matched words, how) for one client."""
    for words in profile['short_forms']:
        hits = [word_matches(w, said) for w in words]
        if all(hits):
            return DICTIONARY, hits, 'dictionary'
    where = [hit for hit in (word_matches(w, said) for w in profile['address']) if hit]
    support = [hit for hit in (word_matches(w, said) for w in profile['support']) if hit] + where
    best = (0.0, [], None)
    for key in profile['keys']:
        hits = [word_matches(w, said) for w in key]
        if all(hits):
            extra = [w for w in support if w not in hits]
            score = min(AUTO_MAX, KEY + SUPPORT * len(extra))
            if score > best[0]:
                best = (score, hits + extra, 'name')
    # city and street without a name: a hint for the manager, never a confirmation
    where = list(dict.fromkeys(where))
    if best[0] == 0 and len(where) >= 2:
        best = (min(.45, .3 + SUPPORT * (len(where) - 1)), where, 'address')
    return best


def head_words(transcript, catalog):
    """Words before the first product word: where the client and address are said."""
    vocab = catalog_vocabulary(catalog or [])
    head = []
    for w in normalize(transcript).split()[:HEAD_WORDS]:
        if _known(w, vocab):
            break
        head.append(w)
    return head


def _rank(clients, said, dictionary_entries):
    scored = []
    for client in clients:
        score, hits, how = score_client(client_profile(client, dictionary_entries), said)
        if score:
            scored.append((score, hits, how, client))
    scored.sort(key=lambda row: (-row[0], normalize(row[3].get('name'))))
    return scored


def detect_client(transcript, clients, catalog=None, dictionary_entries=None):
    """Return {client_id, name, public_name, code, said, matched_by, confidence,
    needs_review, review_reason, candidates} or None when the branch has no
    client list. The client is looked for at the start of the message; when not
    found there — in the rest of it, outside product words."""
    if not clients:
        return None
    said = [w for w in head_words(transcript, catalog) if len(w) >= 3]
    scored = _rank(clients, said, dictionary_entries)
    if not scored:
        vocab = catalog_vocabulary(catalog or [])
        rest = [w for w in normalize(transcript).split() if len(w) >= 3 and not _known(w, vocab)]
        scored = _rank(clients, rest, dictionary_entries)
    candidates = [{'id': str(c['id']), 'name': c['name'], 'confidence': round(s, 2)}
                  for s, _, _, c in scored[:3]]
    if not scored:
        return {'client_id': None, 'name': None, 'public_name': None, 'code': None,
                'said': ' '.join(said), 'matched_by': None, 'confidence': 0.0, 'needs_review': True,
                'review_reason': 'Клиент не назван или не найден в справочнике клиентов',
                'candidates': []}
    score, hits, how, client = scored[0]
    rivals = [c for s, _, _, c in scored[1:] if round(score - s, 3) < MARGIN]
    reasons = []
    if how == 'address':
        reasons.append('Назван только адрес: ' + ', '.join(hits))
    elif score < CONFIRM:
        reasons.append('Клиент назван неполно')
    if rivals:
        reasons.append('Подходят несколько клиентов: ' + '; '.join(c['name'] for c in rivals[:3]))
    return {'client_id': str(client['id']), 'name': client['name'],
            'public_name': client.get('public_name'), 'code': client.get('code'),
            'said': ' '.join(hits), 'matched_by': how, 'confidence': round(score, 2),
            'needs_review': bool(reasons), 'review_reason': '; '.join(reasons),
            'candidates': candidates}


def alias_conflicts(clients, dictionary_entries=None):
    """Key words and short forms shared by several clients: said alone they
    cannot pick the client, the manager should add a distinct short form."""
    owners = {}
    for client in clients or []:
        profile = client_profile(client, dictionary_entries)
        for words in profile['keys'] + profile['short_forms']:
            owners.setdefault(' '.join(words), set()).add(str(client['id']))
    by_id = {str(c['id']): c for c in clients or []}
    return [{'said': said, 'clients': [{'id': i, 'name': by_id[i]['name']} for i in sorted(ids)]}
            for said, ids in sorted(owners.items()) if len(ids) > 1]
