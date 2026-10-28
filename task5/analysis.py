import io
import csv
import re
from urllib.parse import urlparse
import numpy as np
import pandas as pd
import requests
from scipy.stats import t


def sheet_csv_url(value):
    match = re.fullmatch(r'[A-Za-z0-9_-]{20,100}', value)
    if match:
        identifier = value
    else:
        parsed = urlparse(value)
        match = re.match(r'/spreadsheets/d/([A-Za-z0-9_-]{20,100})(?:/|$)', parsed.path)
        if parsed.scheme != 'https' or parsed.hostname != 'docs.google.com' or not match:
            raise ValueError('Use a public Google Sheets URL or spreadsheet ID')
        identifier = match[1]
    return f'https://docs.google.com/spreadsheets/d/{identifier}/gviz/tq?tqx=out:csv&sheet=Data'


def read_source(source=None, sample_path=None):
    if source:
        response = requests.get(sheet_csv_url(source), timeout=25, allow_redirects=True)
        response.raise_for_status()
        if len(response.content) > 5_000_000:
            raise ValueError('Spreadsheet export exceeds the 5 MB limit')
        content = response.text
        if '<html' in content[:1000].lower() or '<!doctype' in content[:1000].lower():
            raise ValueError('Spreadsheet is not publicly readable or has no Data sheet')
    else:
        content = sample_path.read_text(encoding='utf-8')
    headings = next(csv.reader(io.StringIO(content)), [])
    populated_headings = [name for name in headings if name.strip()]
    if len(set(populated_headings)) != len(populated_headings):
        raise ValueError('Each active mine column must have a unique name')
    table = pd.read_csv(io.StringIO(content), thousands=',')
    if 'Date' not in table:
        raise ValueError('Data sheet must contain a Date column')
    table = table.loc[table['Date'].notna()].copy()
    if not 1 <= len(table) <= 366:
        raise ValueError('Provide between 1 and 366 dated observations')
    table['Date'] = pd.to_datetime(table['Date'], format='mixed', errors='raise')
    if table['Date'].duplicated().any():
        raise ValueError('Data contains duplicate calendar dates')
    mines = [name for name in table if name not in ['Date', 'Total', 'Chart date'] and not str(name).startswith('Unnamed:')]
    if not mines or len(mines) > 20:
        raise ValueError('Provide between 1 and 20 named mine columns')
    for name in mines:
        table[name] = pd.to_numeric(table[name], errors='raise')
    values = table[mines].to_numpy(dtype=float)
    if not len(table) or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Mine output must be finite and nonnegative for every date')
    table = table.sort_values('Date').reset_index(drop=True)
    table['Total'] = table[mines].sum(axis=1)
    return table[['Date', *mines, 'Total']], mines


def grubbs_flags(values, alpha):
    remaining = list(range(len(values)))
    flags = set()
    while len(remaining) >= 3:
        sample = values[remaining]
        deviation = np.std(sample, ddof=1)
        if deviation == 0:
            break
        distances = np.abs(sample - np.mean(sample))
        worst = int(np.argmax(distances))
        size = len(remaining)
        critical_t = t.ppf(1 - alpha / (2 * size), size - 2)
        critical_g = (size - 1) / np.sqrt(size) * np.sqrt(critical_t ** 2 / (size - 2 + critical_t ** 2))
        if distances[worst] / deviation <= critical_g:
            break
        flags.add(remaining.pop(worst))
    return flags


def analyze_series(name, dates, values, parameters):
    values = np.asarray(values, dtype=float)
    q1, q3 = np.quantile(values, [0.25, 0.75])
    mean = float(np.mean(values))
    deviation = float(np.std(values, ddof=0))
    iqr = float(q3 - q1)
    moving = pd.Series(values).shift(1).rolling(parameters['window'], min_periods=parameters['window']).mean()
    grubbs = grubbs_flags(values, parameters['alpha'])
    anomalies = []
    for index, value in enumerate(values):
        tests = []
        if value < q1 - parameters['iqr'] * iqr or value > q3 + parameters['iqr'] * iqr:
            tests.append('IQR')
        if deviation > 0 and abs(value - mean) / deviation > parameters['z']:
            tests.append('z-score')
        baseline = moving.iloc[index]
        if pd.notna(baseline):
            if baseline == 0:
                moving_outlier = value != 0
            else:
                moving_outlier = abs(value - baseline) / abs(baseline) * 100 > parameters['moving_percent']
            if moving_outlier:
                tests.append('Moving average')
        if index in grubbs:
            tests.append('Grubbs')
        if tests:
            reference = float(baseline) if pd.notna(baseline) else mean
            anomalies.append({
                'index': index, 'date': dates[index], 'value': float(value),
                'kind': 'spike' if value > reference else 'drop', 'tests': tests,
            })
    degree = parameters['degree']
    trend = None
    if len(values) >= degree + 1:
        x = np.linspace(-1, 1, len(values))
        model = np.polynomial.Polynomial.fit(x, values, degree)
        trend = [float(value) for value in model(x)]
    return {
        'name': name, 'count': len(values), 'total': float(np.sum(values)),
        'mean': mean, 'standard_deviation': deviation, 'median': float(np.median(values)),
        'q1': float(q1), 'q3': float(q3), 'iqr': iqr,
        'values': values.tolist(), 'trend': trend, 'anomalies': anomalies,
    }


def validate_parameters(arguments):
    result = {
        'iqr': float(arguments.get('iqr', 1.5)),
        'z': float(arguments.get('z', 3)),
        'window': int(arguments.get('window', 7)),
        'moving_percent': float(arguments.get('moving_percent', 35)),
        'alpha': float(arguments.get('alpha', 0.05)),
        'degree': int(arguments.get('degree', 1)),
    }
    if not all(np.isfinite(value) for value in result.values()):
        raise ValueError('Analysis parameters must be finite')
    if not (0 < result['iqr'] <= 10 and 0 < result['z'] <= 10 and 1 <= result['window'] <= 60):
        raise ValueError('IQR/z thresholds must be positive; moving window must be 1..60')
    if not (0 < result['moving_percent'] <= 1000 and 0 < result['alpha'] < 1 and 1 <= result['degree'] <= 4):
        raise ValueError('Invalid moving threshold, Grubbs alpha or polynomial degree')
    return result


def analyze(table, mines, parameters):
    dates = table['Date'].dt.strftime('%Y-%m-%d').tolist()
    return {
        'dates': dates, 'parameters': parameters,
        'series': [analyze_series(name, dates, table[name].to_numpy(dtype=float), parameters) for name in [*mines, 'Total']],
        'notes': {
            'standard_deviation': 'Population standard deviation (ddof=0); Grubbs uses sample standard deviation internally.',
            'moving_average': 'Previous N observed rows; current point excluded; no test before a full window is available.',
            'grubbs': 'Iterative two-sided Grubbs test; assumes an approximately normal baseline.',
            'trend': 'Least-squares polynomial; unavailable if there are fewer than degree+1 observations.',
        },
    }
