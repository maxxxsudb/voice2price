"""Re-import of a branch catalog (nomenclature or clients) from 1C without duplicates.

Each row of the new file is matched to a row already in the database: by the 1C
code, then by article + name, then by name. A matched row is updated in place,
so its ID, realistic limit, pronunciation variants and old orders stay. Rows
that are no longer in the file are hidden (import_status='removed'), not
deleted: old orders keep their references. Duplicates left by earlier imports
match nothing and are hidden as well.
"""
import re
from collections import defaultdict

REMOVED = 'removed'


def _text(value):
    return ' '.join(str(value or '').lower().replace('ё', 'е').split())


def nomenclature_keys(row):
    name = _text(row.get('name'))
    keys = []
    if _text(row.get('code')):
        keys.append(('code', _text(row.get('code'))))
    if _text(row.get('article')) and name:
        keys.append(('article', _text(row.get('article')), name))
    if name:
        keys.append(('name', re.sub(r'\s+', ' ', name)))
    return keys


def client_keys(row):
    keys = []
    if _text(row.get('code')):
        keys.append(('code', _text(row.get('code'))))
    if _text(row.get('name')):
        keys.append(('name', _text(row.get('name'))))
    return keys


def plan(existing, incoming, keys):
    """existing: rows in the DB (dicts with 'id'); incoming: rows of the file.
    Returns (matches [(existing_id, row)], new_rows, removed_ids).
    Every existing row is used at most once; the oldest (first) wins."""
    index = defaultdict(list)
    for row in existing:
        for key in keys(row):
            index[key].append(row['id'])
    used, matches, new_rows = set(), [], []
    for row in incoming:
        match = None
        for key in keys(row):
            match = next((i for i in index.get(key, []) if i not in used), None)
            if match:
                break
        if match:
            used.add(match)
            matches.append((match, row))
        else:
            new_rows.append(row)
    removed = [row['id'] for row in existing if row['id'] not in used]
    return matches, new_rows, removed
