"""One order from several voice messages.

Customers often split an order: «...рулет индейка запеченный» / next message
«два с половиной килограмма, зельц...». Messages are sorted by recording time
and joined into one order when nothing says they are different orders:
  * a gap longer than merge_window_min starts a new order;
  * two different named clients start a new order;
  * otherwise a message joins the previous one when it is the same client,
    starts with a quantity, follows a message that ended with a name without a
    quantity, or was recorded within the window and names no client.
Every merge carries its reason, so the manager sees why messages were joined.
"""
import re
from datetime import datetime

from order_pipeline import parse_order, usable_catalog
from order_segmenter import normalize, segment
from order_settings import clean
from spoken_quantity import parse_at, tokens

STAMP = re.compile(r'(20\d\d)[-_.]?(\d\d)[-_.]?(\d\d)[ _T-]+(\d\d)[-_.:]?(\d\d)[-_.:]?(\d\d)')


def time_source(file_name):
    return 'name' if STAMP.search(str(file_name or '')) else 'file'


def recorded_at(file_name, last_modified=None):
    """Seconds since epoch: from the file name («2026-08-23 21-37-42.mp3»,
    «audio_2026-08-23_21-37-42.ogg», «20260823_213742.m4a»), else the file time."""
    match = STAMP.search(str(file_name or ''))
    if match:
        try:
            return datetime(*map(int, match.groups())).timestamp()
        except ValueError:
            pass
    if isinstance(last_modified, (int, float)) and not isinstance(last_modified, bool) and last_modified > 0:
        return last_modified / 1000 if last_modified > 1e11 else float(last_modified)
    return None


def starts_with_quantity(text):
    words = tokens(normalize(text))
    return bool(words) and parse_at(words, 0) is not None


def ends_without_quantity(text, catalog):
    items = segment(text, catalog)
    return bool(items) and items[-1]['quantity'] is None


def _merge_reason(group, message, settings, catalog):
    """Why `message` continues `group`, or None when it is a new order."""
    last = group[-1]
    gap = None
    # a time from a file name (local time) and a file date are not comparable
    if (last['time'] is not None and message['time'] is not None
            and last['source'] == message['source']):
        gap = message['time'] - last['time']
        if gap > settings['merge_window_min'] * 60 or gap < 0:
            return None
    group_client = next((m['client_id'] for m in group if m['client_id']), None)
    if group_client and message['client_id'] and message['client_id'] != group_client:
        return None
    if group_client and message['client_id'] == group_client:
        return 'тот же клиент'
    if starts_with_quantity(message['text']):
        return 'сообщение начинается с количества — продолжение предыдущего'
    if ends_without_quantity(last['text'], catalog):
        return 'предыдущее сообщение закончилось названием без количества'
    if gap is not None and not message['client_id']:
        return f'записано через {int(gap // 60)} мин {int(gap % 60)} с, клиент не назван'
    return None


def group_messages(messages, settings, catalog, client_of=lambda text: None):
    """messages: [{id, file_name, text, last_modified}] -> list of groups (lists)."""
    prepared = []
    for n, m in enumerate(messages):
        client = client_of(m.get('text') or '')
        prepared.append({
            'id': str(m.get('id') or n), 'file_name': m.get('file_name') or '',
            'text': m.get('text') or '', 'order': n,
            'time': recorded_at(m.get('file_name'), m.get('last_modified')),
            'source': time_source(m.get('file_name')),
            'client': client, 'client_id': (client or {}).get('client_id'),
        })
    # by recording time when every message has one, else in upload order
    if all(m['time'] is not None for m in prepared) and len({m['source'] for m in prepared}) == 1:
        prepared.sort(key=lambda m: (m['time'], m['order']))
    groups = []
    for message in prepared:
        reason = (_merge_reason(groups[-1], message, settings, catalog)
                  if groups and settings['merge_messages'] and message['text'].strip() else None)
        if reason:
            message['merge_reason'] = reason
            groups[-1].append(message)
        else:
            groups.append([message])
    return groups


def parse_messages(messages, catalog_rows, clients=None, dictionary_entries=None, settings=None):
    """Voice messages of one branch -> orders, one per client conversation."""
    from client_matching import detect_client
    settings = clean(settings)
    catalog = usable_catalog(catalog_rows)

    def client_of(text):
        if not settings['detect_client'] or not clients:
            return None
        return detect_client(text, clients, catalog, dictionary_entries)

    orders = []
    for group in group_messages(messages, settings, catalog, client_of):
        text = ' '.join(m['text'].strip() for m in group if m['text'].strip())
        clients_found = [m['client'] for m in group if m['client']]
        client = next((c for c in clients_found if c.get('client_id') and not c['needs_review']),
                      next((c for c in clients_found if c.get('client_id')),
                           clients_found[0] if clients_found else None))
        orders.append({
            'message_ids': [m['id'] for m in group],
            'file_names': [m['file_name'] for m in group],
            'merged': len(group) > 1,
            'merge_reasons': [f'{m["file_name"] or m["id"]}: {m["merge_reason"]}'
                              for m in group[1:]],
            'text': text,
            'client': client,
            'order_items': parse_order(text, catalog_rows, dictionary_entries=dictionary_entries,
                                       settings=settings) if text else [],
        })
    return orders
