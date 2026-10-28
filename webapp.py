import csv
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from flask import Flask, jsonify, request, send_file, send_from_directory
import psycopg
import requests
from task5.analysis import analyze, read_source, validate_parameters
from task5.report import create_report
from task6.setup_database import setup

BASE = Path(__file__).resolve().parent
app = Flask(__name__, static_folder='web', static_url_path='/assets')
app.config['MAX_CONTENT_LENGTH'] = 5_000_000
SHEET_ID = '1V1jk3IbcGMjZDNJ41Jo7bEDaei9JrHGrlZ-k3UVdfgs'
DATABASE_URL = os.environ.get('DATABASE_URL', '')


@app.errorhandler(ValueError)
def invalid_request(error):
    return jsonify(error=str(error)), 400


@app.errorhandler(400)
def bad_request(error):
    return jsonify(error='Provide a valid JSON request and valid parameters'), 400


@app.errorhandler(requests.RequestException)
def unavailable_sheet(error):
    return jsonify(error='Could not read the Google Sheets export. Check the link, the Data tab and public view access.'), 502


@app.errorhandler(psycopg.Error)
def unavailable_database(error):
    app.logger.error('SQL operation failed: %s', error.sqlstate)
    return jsonify(error='The database could not complete the request. Check the local server and generation parameters.'), 503


@app.get('/')
def home():
    return send_from_directory(BASE / 'web', 'index.html')


@app.get('/health')
def health():
    return jsonify(status='ok', sql_generator_configured=bool(DATABASE_URL))


@app.get('/task4/')
@app.get('/task4/<path:filename>')
def bookstore(filename='index.html'):
    return send_from_directory(BASE / 'task4' / 'web', filename)


@app.get('/api/status')
def ai_status():
    return jsonify(configured=False, model=None, reason='Live AI integration is pending API key setup')


@app.post('/api/chat')
def ai_chat():
    return jsonify(error='Живая AI-интеграция пока не подключена: создание API-ключа не завершено. Расчёты dashboard доступны.'), 503


@app.get('/api/task5')
def mine_analytics():
    parameters = validate_parameters(request.args)
    source = request.args.get('source', '')
    table, mines = read_source(source=source or None, sample_path=BASE / 'task5' / 'sample.csv')
    result = analyze(table, mines, parameters)
    result['source'] = 'Google Sheets live export' if source else 'Included snapshot of the formula-generated sheet'
    result['spreadsheet_url'] = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit'
    return jsonify(result)


@app.get('/api/task5/report.pdf')
def mine_pdf():
    parameters = validate_parameters(request.args)
    source = request.args.get('source', '')
    table, mines = read_source(source=source or None, sample_path=BASE / 'task5' / 'sample.csv')
    content = create_report(analyze(table, mines, parameters))
    return send_file(io.BytesIO(content), mimetype='application/pdf', as_attachment=True, download_name='mine-production-report.pdf')


def generation_arguments():
    locale = request.args.get('locale', 'en_US')
    seed_text = request.args.get('seed', '42')
    if not re.fullmatch(r'-?\d{1,19}', seed_text):
        raise ValueError('Seed must be a signed 64-bit integer')
    seed = int(seed_text)
    batch = int(request.args.get('batch', 0))
    size = int(request.args.get('size', 10))
    if locale not in ['en_US', 'de_DE'] or not -(2 ** 63) <= seed < 2 ** 63:
        raise ValueError('Choose en_US/de_DE and a signed 64-bit seed')
    if not 0 <= batch <= 1_000_000_000 or not 1 <= size <= 100:
        raise ValueError('Batch must be 0..1000000000; page size must be 1..100')
    return locale, seed, batch, size


@app.get('/api/task6')
def fake_contacts():
    if not DATABASE_URL:
        return jsonify(error='PostgreSQL is not configured. Start the application with the supplied local launcher.'), 503
    locale, seed, batch, size = generation_arguments()
    start = time.perf_counter()
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute("SET statement_timeout = '15s'")
        rows = connection.execute('CALL fake.generate_users(%s,%s,%s,%s,NULL)', (locale, seed, batch, size)).fetchone()[0]
    elapsed = time.perf_counter() - start
    return jsonify(users=rows, locale=locale, seed=str(seed), batch=batch, size=size, seconds=elapsed, users_per_second=size / elapsed)


@app.get('/task6/docs')
def procedure_docs():
    return send_from_directory(BASE / 'task6', 'documentation.html')


@app.get('/source/<task>/<filename>')
def source_code(task, filename):
    allowed = {
        'task35': {'main.py', 'schema.sql', 'summary.sql', 'show_database.py'},
        'task6': {'schema.sql', 'setup_database.py'},
    }
    if filename not in allowed.get(task, set()):
        return jsonify(error='Source file is not available'), 404
    return send_file(BASE / task / filename, mimetype='text/plain')


@app.get('/api/task35')
def books_summary():
    with sqlite3.connect(BASE / 'task35' / 'results' / 'books.sqlite') as connection:
        connection.row_factory = sqlite3.Row
        tables = [dict(row) for row in connection.execute('SELECT * FROM summary ORDER BY publication_year')]
        count = connection.execute('SELECT COUNT(*) FROM books').fetchone()[0]
        example = [dict(row) for row in connection.execute('SELECT * FROM books LIMIT 8')]
        integrity = connection.execute('PRAGMA integrity_check').fetchone()[0]
    return jsonify(books=count, summary_rows=len(tables), integrity=integrity, summary=tables, example_books=example)


@app.get('/api/config')
def configuration():
    return jsonify(sheet_id=SHEET_ID, sheet_url=f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit')


def main():
    if DATABASE_URL:
        counts = setup(DATABASE_URL)
        print(f'SQL lookup categories ready: {len(counts)}', flush=True)
    app.run(host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', '8095')), debug=False)


if __name__ == '__main__':
    main()
