import csv
import hashlib
from pathlib import Path
import psycopg

BASE = Path(__file__).resolve().parent


def setup(database_url):
    with psycopg.connect(database_url) as connection:
        connection.execute((BASE / 'schema.sql').read_text(encoding='utf-8'))
        connection.execute("SELECT pg_advisory_xact_lock(hashtext('ilearning.fake.lookup-import'))")
        connection.execute('CREATE TABLE IF NOT EXISTS fake.lookup_version (singleton BOOLEAN PRIMARY KEY CHECK (singleton), digest TEXT NOT NULL)')
        digest = hashlib.sha256((BASE / 'lookup_words.csv').read_bytes()).hexdigest()
        existing = connection.execute('SELECT digest FROM fake.lookup_version WHERE singleton = TRUE').fetchone()
        if not existing or existing[0] != digest:
            connection.execute('TRUNCATE fake.words')
            with (BASE / 'lookup_words.csv').open(encoding='utf-8', newline='') as stream:
                reader = csv.reader(stream)
                next(reader)
                with connection.cursor().copy('COPY fake.words (locale,category,position,value) FROM STDIN') as copy:
                    for row in reader:
                        copy.write_row(row)
            connection.execute('INSERT INTO fake.lookup_version VALUES (TRUE,%s) ON CONFLICT (singleton) DO UPDATE SET digest = EXCLUDED.digest', (digest,))
        connection.execute('DELETE FROM fake.word_counts')
        connection.execute(
            'INSERT INTO fake.word_counts SELECT locale, category, COUNT(*) FROM fake.words GROUP BY locale, category'
        )
        return connection.execute(
            'SELECT locale, category, amount FROM fake.word_counts ORDER BY locale, category'
        ).fetchall()
