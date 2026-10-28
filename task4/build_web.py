
import json
from pathlib import Path
import sqlite3
BASE=Path(__file__).resolve().parent
(BASE/'web/data.json').write_bytes((BASE/'results/dashboard_data.json').read_bytes())
with sqlite3.connect(BASE/'results/analytics.sqlite') as connection:
    connection.row_factory=sqlite3.Row
    for number in range(1,6):
        store=f'STORE{number}'
        rows=[dict(r) for r in connection.execute('SELECT id,title,author,genre,year FROM books WHERE store=? ORDER BY title',(store,))]
        (BASE/f'web/catalog-{store}.json').write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
print('Web data refreshed for STORE1..STORE5.')
