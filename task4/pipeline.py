






from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import hashlib
from itertools import combinations
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

import pandas as pd
import yaml

BASE = Path(__file__).resolve().parent
RATE = Decimal('1.2')
MISSING = {'', 'null', 'none', 'nan', 'n/a', 'na'}
MONTHS = {name[:3].casefold(): i for i, name in enumerate(
    ['January', 'February', 'March', 'April', 'May', 'June', 'July',
     'August', 'September', 'October', 'November', 'December'], 1)}
DATE_PATTERNS = [
    ('iso', re.compile(r'(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)')),
    ('us_slash', re.compile(r'(?<!\d)(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})(?!\d)')),
    ('eu_dot', re.compile(r'(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)')),
    ('named_month', re.compile(r'(?<!\d)(\d{1,2})-([A-Za-z]+)-(\d{4})(?!\d)')),
]
TIME = re.compile(r'^(\d{1,2}):(\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?\s*(AM|PM)?$', re.I)


def clean_text(value):
    if value is None or pd.isna(value):
        return None
    text = ' '.join(unicodedata.normalize('NFKC', str(value)).split())
    return None if text.casefold() in MISSING else text


def positive_int(value):
    text = clean_text(value)
    if text is None or not re.fullmatch(r'\d+(?:\.0+)?', text):
        raise ValueError('expected a positive integer')
    number = int(Decimal(text))
    if number <= 0:
        raise ValueError('expected a positive integer')
    return number


def parse_money(value):

    text = clean_text(value)
    if text is None:
        raise ValueError('missing unit_price')
    compact = re.sub(r'\s+', '', text).upper()
                                                                
    match = re.fullmatch(r'([$€])(\d+)¢(\d{1,2})', compact)
    if match:
        symbol, whole, cents = match.groups()
        return ('USD' if symbol == '$' else 'EUR', Decimal(whole) + Decimal(cents) / 100)
    match = re.fullmatch(r'(\d+)([$€])(\d{1,2})¢', compact)
    if match:
        whole, symbol, cents = match.groups()
        return ('USD' if symbol == '$' else 'EUR', Decimal(whole) + Decimal(cents) / 100)
    match = re.fullmatch(r'(USD|EUR|\$|€)?(\d+(?:\.\d{0,2})?)(USD|EUR|\$|€)?', compact)
    if not match:
        raise ValueError('unrecognized unit_price syntax')
    prefix, amount, suffix = match.groups()
    if bool(prefix) == bool(suffix):
        raise ValueError('exactly one currency marker is required')
    return ('USD' if (prefix or suffix) in {'USD', '$'} else 'EUR', Decimal(amount))


def usd_cents(amount):
    return int((amount * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def parse_timestamp(value):






    text = clean_text(value)
    if text is None:
        raise ValueError('missing timestamp')
    text = re.sub(r'([AP])\.M\.', r'\1M', text, flags=re.I)
                                               
    ctime = re.fullmatch(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun) ([A-Za-z]+) (\d{1,2}) (\d{1,2}:\d{2}:\d{2}) (\d{4})', text)
    if ctime:
        weekday, month, day, time_text, year = ctime.groups()
        result = _combine(int(year), MONTHS[month[:3].casefold()], int(day), time_text)
        if ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')[result.weekday()] != weekday:
            raise ValueError('weekday does not match calendar date')
        return result, 'ctime'
    for kind, pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        a, b, c = match.groups()
        if kind == 'iso':
            year, month, day = int(a), int(b), int(c)
        elif kind == 'us_slash':
            year, month, day = int(c) + (2000 if len(c) == 2 else 0), int(a), int(b)
        elif kind == 'eu_dot':
            year, month, day = int(c), int(b), int(a)
        else:
            if b[:3].casefold() not in MONTHS:
                raise ValueError('unknown month name')
            year, month, day = int(c), MONTHS[b[:3].casefold()], int(a)
        remainder = (text[:match.start()] + text[match.end():]).strip(' ,;T')
        return _combine(year, month, day, remainder), kind
    raise ValueError('no complete supported calendar date in timestamp')


def _combine(year, month, day, time_text):
    match = TIME.fullmatch(time_text)
    if not match:
        raise ValueError('invalid clock or trailing timestamp text')
    hour, minute, second, fraction, meridiem = match.groups()
    hour = int(hour)
    if meridiem:
        if not 1 <= hour <= 12:
            raise ValueError('AM/PM hour is outside 1..12')
        hour = hour % 12 + (12 if meridiem.upper() == 'PM' else 0)
    return datetime(year, month, day, hour, int(minute), int(second or 0), int((fraction or '').ljust(6, '0')))


def author_set(value):
    text = clean_text(value)
    if text is None:
        raise ValueError('missing author')
    names = [clean_text(part) for part in text.split(',')]
    if any(name is None for name in names):
        raise ValueError('empty author in list')
                                                                                  
    by_key = {}
    for name in names:
        by_key.setdefault(name.casefold(), name)
    return tuple(by_key[key] for key in sorted(by_key))


def identity_value(field, value):
    value = clean_text(value)
    if value is None:
        return None
    if field == 'phone':
        return re.sub(r'\D', '', value) or None
    return value.casefold()


def reconcile_users(users):





    fields = ('name', 'address', 'phone', 'email')
    parent = {int(uid): int(uid) for uid in users.id}

    def find(uid):
        while parent[uid] != uid:
            parent[uid] = parent[parent[uid]]
            uid = parent[uid]
        return uid

    def union(a, b):
        a, b = find(a), find(b)
        parent[max(a, b)] = min(a, b)

    seen, links, normalized = {}, [], {}
    for row in users.sort_values('id').to_dict('records'):
        uid = int(row['id'])
        values = tuple(identity_value(field, row[field]) for field in fields)
        normalized[uid] = values
        for indexes in combinations(range(4), 3):
            projected = tuple(values[i] for i in indexes)
            if None in projected:
                continue
            key = indexes, projected
            if key in seen:
                other = seen[key]
                if find(uid) != find(other):
                    links.append({'user_id_a': other, 'user_id_b': uid,
                                  'matching_fields': [fields[i] for i in indexes]})
                    union(uid, other)
            else:
                seen[key] = uid
    mapping = {uid: find(uid) for uid in parent}
                                                                           
                                                                     
    candidates, pair_seen = [], set()
    pair_buckets = defaultdict(list)
    for uid, values in normalized.items():
        for indexes in combinations(range(4), 2):
            projected = tuple(values[i] for i in indexes)
            if None not in projected:
                pair_buckets[indexes, projected].append(uid)
    for ids in pair_buckets.values():
        for a, b in combinations(ids, 2):
            if mapping[a] == mapping[b] or (a, b) in pair_seen:
                continue
            pair_seen.add((a, b))
            va, vb = normalized[a], normalized[b]
            equal = [fields[i] for i in range(4) if va[i] is not None and va[i] == vb[i]]
            conflicts = [fields[i] for i in range(4) if va[i] is not None and vb[i] is not None and va[i] != vb[i]]
            if len(equal) >= 2 and len(conflicts) <= 1 and (None in va or None in vb):
                candidates.append({'user_id_a': a, 'user_id_b': b, 'matching_fields': equal, 'conflicting_fields': conflicts})
    return mapping, links, candidates


def unique_records(frame, table, audit):
    audit[f'{table}_input_rows'] = len(frame)
    duplicate_mask = frame.duplicated()
    audit[f'{table}_exact_duplicates_removed'] = int(duplicate_mask.sum())
    frame = frame.loc[~duplicate_mask].copy()
    if frame.id.duplicated().any():
        raise ValueError(f'{table}: conflicting rows with the same id; manual resolution required')
    return frame


def process_store(folder, output, connection):
    store = folder.name
    audit = {}
    quarantine = []
    users = unique_records(pd.read_csv(folder / 'users.csv', dtype=str, keep_default_na=False), 'users', audit)
    for column in users:
        users[column] = users[column].map(clean_text)
    users['id'] = users.id.map(positive_int)
    for field in ('name', 'address', 'phone', 'email'):
        audit[f'users_missing_{field}'] = int(users[field].isna().sum())
                                                                               
                                                                              
                                                               
    bad_email = users.email.notna() & ~users.email.fillna('').str.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    bad_phone = users.phone.notna() & ~users.phone.fillna('').map(lambda x: bool(re.fullmatch(r'[\d\s()+.\-]+', x)) and len(re.sub(r'\D', '', x)) >= 7)
    audit['users_malformed_email'] = int(bad_email.sum())
    audit['users_malformed_phone'] = int(bad_phone.sum())
    users.loc[bad_email, 'email'] = None
    users.loc[bad_phone, 'phone'] = None
    mapping, links, candidates = reconcile_users(users)
    users['canonical_user_id'] = users.id.map(mapping)
    audit['identity_links'] = len(links)
    audit['identity_unresolved_candidate_pairs'] = len(candidates)

    raw_books = yaml.safe_load((folder / 'books.yaml').read_text(encoding='utf-8'))
    books = unique_records(pd.DataFrame(raw_books).rename(columns=lambda x: x.lstrip(':')), 'books', audit)
    books['id'] = books.id.map(positive_int)
    for field in ('title', 'author', 'genre', 'publisher'):
        books[field] = books[field].map(clean_text)
    audit['books_missing_publisher'] = int(books.publisher.isna().sum())
    years = pd.to_numeric(books.year.map(clean_text), errors='coerce')
    valid_year = years.notna() & (years % 1 == 0) & years.between(1, 9999)
    audit['books_missing_or_malformed_year'] = int((~valid_year).sum())
    books['year'] = years.where(valid_year).astype('Int64')
                                                                               
                                                                             
    books['authors'] = books.author.map(author_set)
    books['author_set_key'] = books.authors.map(lambda a: json.dumps([s.casefold() for s in a], ensure_ascii=False))
    books['authors_json'] = books.authors.map(lambda a: json.dumps(a, ensure_ascii=False))
    authors_display = books.set_index('author_set_key').authors.to_dict()

    raw_orders = unique_records(pd.read_parquet(folder / 'orders.parquet'), 'orders', audit)
    valid_users, valid_books = set(users.id), set(books.id)
    records, format_counts, currency_counts = [], Counter(), Counter()
    rounding_difference = 0
    for row in raw_orders.to_dict('records'):
        try:
            order_id, uid, bid, quantity = (positive_int(row[key]) for key in ('id', 'user_id', 'book_id', 'quantity'))
            if uid not in valid_users or bid not in valid_books:
                raise ValueError('orphan user_id or book_id')
            currency, source_amount = parse_money(row['unit_price'])
            unit_usd = source_amount * (RATE if currency == 'EUR' else Decimal(1))
            paid_cents = usd_cents(unit_usd * quantity)
            timestamp, timestamp_format = parse_timestamp(row['timestamp'])
            records.append({'id': order_id, 'user_id': uid, 'canonical_user_id': mapping[uid],
                            'book_id': bid, 'quantity': quantity, 'source_currency': currency,
                            'source_unit_price': str(source_amount), 'unit_price_usd': str(unit_usd),
                            'unit_price_cents': usd_cents(unit_usd), 'paid_price_cents': paid_cents,
                            'paid_price': f'{Decimal(paid_cents) / 100:.2f}',
                            'timestamp': timestamp, 'timestamp_raw': row['timestamp'],
                            'date': timestamp.strftime('%Y-%m-%d'), 'timestamp_format': timestamp_format,
                            'shipping': clean_text(row['shipping'])})
            format_counts[timestamp_format] += 1
            currency_counts[currency] += 1
            rounding_difference += usd_cents(unit_usd) * quantity - paid_cents
        except (ValueError, KeyError, TypeError) as exc:
            quarantine.append({**row, 'reason': str(exc)})
    orders = pd.DataFrame(records)
    if orders.empty:
        raise ValueError(f'{store}: no valid orders')
    orders['timestamp'] = pd.to_datetime(orders.timestamp)
    audit.update(orders_valid_rows=len(orders), orders_quarantined=len(quarantine),
                 timestamp_formats=dict(format_counts), currencies=dict(currency_counts),
                 orders_missing_shipping=int(orders.shipping.isna().sum()),
                 date_min=orders.date.min(), date_max=orders.date.max(),
                 round_unit_before_quantity_difference_cents=rounding_difference)
    daily = orders.groupby('date', as_index=False).agg(revenue_cents=('paid_price_cents', 'sum'))
                                                                             
    dates = pd.date_range(orders.date.min(), orders.date.max()).strftime('%Y-%m-%d')
    daily = daily.set_index('date').reindex(dates, fill_value=0).rename_axis('date').reset_index()
    top_days = daily.sort_values(['revenue_cents', 'date'], ascending=[False, True]).head(5)
    joined = orders.merge(books[['id', 'author_set_key']], left_on='book_id', right_on='id', validate='many_to_one')
    popularity = joined.groupby('author_set_key', as_index=False).quantity.sum().rename(columns={'quantity': 'books_sold'})
    max_sold = int(popularity.books_sold.max())
    popular = [{'authors': list(authors_display[row.author_set_key]), 'books_sold': int(row.books_sold)}
               for row in popularity[popularity.books_sold == max_sold].sort_values('author_set_key').itertuples()]
    spending = orders.groupby('canonical_user_id').paid_price_cents.sum()
    max_spent = int(spending.max())
    winners = []
    for canonical_id in sorted(int(i) for i in spending[spending == max_spent].index):
        aliases = users[users.canonical_user_id == canonical_id]
        winners.append({'canonical_user_id': canonical_id, 'user_ids': sorted(int(i) for i in aliases.id),
                        'names': sorted({name for name in aliases.name if name is not None}), 'total_spent_cents': max_spent})
    result = {'store': store, 'unique_users': int(users.canonical_user_id.nunique()),
              'unique_author_sets': int(books.author_set_key.nunique()),
              'total_revenue_cents': int(orders.paid_price_cents.sum()),
              'total_books_sold': int(orders.quantity.sum()), 'order_count': len(orders),
              'book_count': len(books), 'user_record_count': len(users),
              'top_days': top_days.to_dict('records'), 'daily_revenue': daily.to_dict('records'),
              'most_popular_author_sets': popular, 'top_customers': winners, 'audit': audit}
    target = output / store
    target.mkdir(parents=True, exist_ok=True)
    daily.to_csv(target / 'daily_revenue.csv', index=False)
    users.to_csv(target / 'users_clean.csv', index=False)
    books.drop(columns='authors').to_csv(target / 'books_clean.csv', index=False)
    orders.to_csv(target / 'orders_clean.csv', index=False)
    (target / 'identity_links.json').write_text(json.dumps(links, ensure_ascii=False, indent=2), encoding='utf-8')
    (target / 'identity_candidates.json').write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding='utf-8')
    (target / 'quarantine.json').write_text(json.dumps(quarantine, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    for name, frame in [('users', users), ('books', books.drop(columns='authors')), ('orders', orders), ('daily_revenue', daily)]:
        frame.assign(store=store).to_sql(name, connection, if_exists='append', index=False)
    return result


def write_report(payload, output):
    lines = ['# Task 4 — воспроизводимый отчёт по данным', '',
             'Суммы рассчитаны локально из приложенных файлов. Официального ответа преподавателя нет; это результаты описанной ниже обработки.', '',
             '| Магазин | Заказы | Реальные пользователи | Наборы авторов | Выручка USD | Продано книг |',
             '|---|---:|---:|---:|---:|---:|']
    for s in payload['stores']:
        lines.append(f"| {s['store']} | {s['order_count']} | {s['unique_users']} | {s['unique_author_sets']} | {s['total_revenue_cents']/100:.2f} | {s['total_books_sold']} |")
    for s in payload['stores']:
        lines += ['', f"## {s['store']}", '',
                  'Топ-5 дней: ' + '; '.join(f"{d['date']}: ${d['revenue_cents']/100:.2f}" for d in s['top_days']) + '.',
                  'Самый популярный набор авторов: ' + '; '.join(', '.join(a['authors']) + f" — {a['books_sold']} экземпляров" for a in s['most_popular_author_sets']) + '.',
                  'Лучший покупатель: ' + '; '.join(json.dumps(c['user_ids']) + f" — ${c['total_spent_cents']/100:.2f}; имена: " + ', '.join(c['names']) for c in s['top_customers']) + '.',
                  f"Период: {s['audit']['date_min']} — {s['audit']['date_max']}. Исключено заказов: {s['audit']['orders_quarantined']}. Неразрешённых пар пользователей: {s['audit']['identity_unresolved_candidate_pairs']}."]
    lines += ['', '## Правила и допущения', '',
              '* Все пять папок обработаны независимо. В тексте задания указаны три вкладки, но архив содержит пять магазинов.',
              '* Даты распознаны по явно проверяемым шаблонам: ISO, MM/DD/YY, DD.MM.YYYY, английские названия месяцев и ctime. Формат с / принят как американский: в тех же данных встречаются 06/16/25. Двузначный год означает 2000–2099. Часовой пояс в источниках отсутствует; сохранён исходный календарный день. Никакого подставления сегодняшней даты.',
              '* USD и EUR распознаны с символами $, €, кодами валют и разделителем ¢. Decimal хранит точные значения. paid_price = quantity × source_unit_price × rate, затем однократное округление HALF_UP до центов. Промежуточная цена USD может иметь долю цента; округлённая unit_price_cents предназначена для отображения. Альтернатива округлять единичную цену раньше отражена отдельной разницей в audit.',
              '* Пустые значения, NULL, NaN, None, N/A преобразованы в отсутствующие. Отсутствующие publisher/year/shipping не удаляют корректные продажи. Полные дубликаты удаляются; противоречивый одинаковый id останавливает обработку. Некорректный заказ попадает в quarantine.json с причиной.',
              '* Идентичность: совпадают три из четырёх известных полей name/address/phone/email; телефон сравнивается по цифрам, остальные поля — без регистра и лишних пробелов. Совпадение отсутствующих значений не считается доказательством. Связанные компоненты объединяют последовательность изменений одного поля. Каждая связь записана в identity_links.json; слабые пары — отдельно в identity_candidates.json и не объединяются молча.',
              '* Набор авторов не зависит от порядка; повтор имени внутри набора удаляется. Количество наборов берётся по всему каталогу. Популярность — сумма quantity проданных книг полного набора авторов, а не число строк заказов. Все равные победители сохраняются.',
              '* Расходы покупателя суммируются по всем идентификаторам его компоненты. В результате возвращаются все связанные id, включая id без покупки. При равенстве суммы показываются все лидеры.',
              '', '## Как проверить', '',
              'Запустите `python pipeline.py`, затем `python -m unittest discover -s tests -v`. Сверьте JSON с SQL-агрегациями в `results/analytics.sqlite`; тесты делают это автоматически. Для каждого магазина сохранены очищенные CSV, ежедневная выручка, связи идентичности и карантин.',
              'Сохранён `source_manifest.json` с SHA-256 исходных файлов. График и веб-интерфейс строятся по `results/dashboard_data.json`.']
    (output / 'DATA_REPORT_RU.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=BASE / 'data')
    parser.add_argument('--output', type=Path, default=BASE / 'results')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    stores = sorted(p for p in args.input.glob('STORE*') if p.is_dir())
    if not stores:
        parser.error(f'no STORE* folders in {args.input}')
    manifest = [{'path': p.relative_to(args.input).as_posix(), 'bytes': p.stat().st_size,
                 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in sorted(args.input.rglob('*')) if p.is_file()]
    (args.output / 'source_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    database = args.output / 'analytics.sqlite'
                                                                                
    with sqlite3.connect(database) as connection:
        for table in ('users', 'books', 'orders', 'daily_revenue'):
            connection.execute(f'DROP TABLE IF EXISTS {table}')
        results = [process_store(folder, args.output, connection) for folder in stores]
        connection.execute('CREATE UNIQUE INDEX users_key ON users(store,id)')
        connection.execute('CREATE UNIQUE INDEX books_key ON books(store,id)')
        connection.execute('CREATE UNIQUE INDEX orders_key ON orders(store,id)')
        connection.execute('CREATE INDEX orders_day ON orders(store,date)')
        connection.execute('CREATE INDEX orders_customer ON orders(store,canonical_user_id)')
    payload = {'schema_version': 1, 'currency': 'USD', 'exchange_rate_eur_usd': str(RATE),
               'rounding': 'ROUND_HALF_UP once per order line after quantity and conversion',
               'stores': results}
    (args.output / 'dashboard_data.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    write_report(payload, args.output)
    for s in results:
        print(f"{s['store']}: {s['order_count']} orders, {s['unique_users']} users, "
              f"{s['unique_author_sets']} author sets, USD {s['total_revenue_cents']/100:.2f}, "
              f"quarantine={s['audit']['orders_quarantined']}, uncertain pairs={s['audit']['identity_unresolved_candidate_pairs']}")


if __name__ == '__main__':
    main()
