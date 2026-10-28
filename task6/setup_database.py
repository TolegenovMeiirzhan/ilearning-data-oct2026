import csv
from pathlib import Path
import psycopg

BASE = Path(__file__).resolve().parent


def setup(database_url):
    with psycopg.connect(database_url) as connection:
        connection.execute((BASE / 'schema.sql').read_text(encoding='utf-8'))
        existing = connection.execute('SELECT COUNT(*) FROM fake.words').fetchone()[0]
        if not existing:
            with (BASE / 'lookup_words.csv').open(encoding='utf-8', newline='') as stream:
                reader = csv.reader(stream)
                next(reader)
                with connection.cursor().copy('COPY fake.words (locale,category,position,value) FROM STDIN') as copy:
                    for row in reader:
                        copy.write_row(row)
        connection.execute('DELETE FROM fake.word_counts')
        connection.execute(
            'INSERT INTO fake.word_counts SELECT locale, category, COUNT(*) FROM fake.words GROUP BY locale, category'
        )
        return connection.execute(
            'SELECT locale, category, amount FROM fake.word_counts ORDER BY locale, category'
        ).fetchall()
