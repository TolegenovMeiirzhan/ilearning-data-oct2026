import json
from pathlib import Path
import sqlite3
import sys
import unittest
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from pipeline import parse_timestamp,parse_money,usd_cents,reconcile_users,author_set,BASE

class DataTests(unittest.TestCase):
    def test_calendar_formats_and_midnight(self):
        for raw,expected in [('06/16/25 1:02 PM','2025-06-16T13:02:00'),('26.01.2025 00:12','2025-01-26T00:12:00'),('1:02 AM 2025-06-16','2025-06-16T01:02:00'),('16-Jun-2025 12:00 AM','2025-06-16T00:00:00'),('Fri Apr 10 15:32:26 2026','2026-04-10T15:32:26'),('2025-06-16T12:00:00','2025-06-16T12:00:00')]:
            with self.subTest(raw=raw):self.assertEqual(parse_timestamp(raw)[0].isoformat(),expected)
    def test_invalid_dates_never_become_today(self):
        for raw in ['','12:00','today','2025-02-30 12:00','2025-01-01 28:00','2025-01-01 13:00 PM']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):parse_timestamp(raw)
    def test_money_syntax(self):
        for raw in ['$70¢50','70$50¢','USD 70.50','70.50 USD','$70.50']:
            self.assertEqual(parse_money(raw),('USD',Decimal('70.50')))
        self.assertEqual(parse_money('€0.99'),('EUR',Decimal('.99')))
        self.assertEqual(usd_cents(Decimal('.99')*3*Decimal('1.2')),356)
        for raw in ['70','USD -3','NaN','$3EUR','€1.234']:
            with self.assertRaises(ValueError):parse_money(raw)
    def test_identity_chain_and_missing(self):
        rows=[(1,'Anna','A','1234567','a@x.test'),(2,'Anya','A','1234567','a@x.test'),(3,'Anya','B','1234567','a@x.test'),(4,'Anna',None,None,'other@x.test'),(5,'Anna',None,None,'other@x.test')]
        mapping,links,candidates=reconcile_users(pd.DataFrame(rows,columns=['id','name','address','phone','email']))
        self.assertEqual([mapping[i] for i in [1,2,3]],[1,1,1]);self.assertNotEqual(mapping[4],mapping[5]);self.assertEqual(len(links),2)
    def test_author_order_is_irrelevant(self):
        self.assertEqual(author_set('Paul, John, Paul'),author_set('John, Paul'))
    def test_actual_source_counts_and_money(self):
        payload=json.loads((BASE/'results/dashboard_data.json').read_text(encoding='utf-8'))
        self.assertEqual(len(payload['stores']),5)
        with sqlite3.connect(BASE/'results/analytics.sqlite') as db:
            for s in payload['stores']:
                name=s['store']
                self.assertEqual(s['audit']['orders_input_rows'],len(pd.read_parquet(BASE/'data'/name/'orders.parquet')))
                count,total,quantity=db.execute('SELECT COUNT(*),SUM(paid_price_cents),SUM(quantity) FROM orders WHERE store=?',(name,)).fetchone()
                self.assertEqual((count,total,quantity),(s['order_count'],s['total_revenue_cents'],s['total_books_sold']))
                independent=0
                for qty,amount,currency,cents in db.execute('SELECT quantity,source_unit_price,source_currency,paid_price_cents FROM orders WHERE store=?',(name,)):
                                                                                        
                    source_cents=int(Decimal(amount)*100);num=source_cents*qty*(6 if currency=='EUR' else 5)
                    expected=(num*2+5)//10
                    self.assertEqual(expected,cents);independent+=expected
                self.assertEqual(independent,total)
    def test_sql_rankings_and_components(self):
        payload=json.loads((BASE/'results/dashboard_data.json').read_text(encoding='utf-8'))
        with sqlite3.connect(BASE/'results/analytics.sqlite') as db:
            for s in payload['stores']:
                store=s['store']
                days=db.execute('SELECT date,SUM(paid_price_cents) amount FROM orders WHERE store=? GROUP BY date ORDER BY amount DESC,date LIMIT 5',(store,)).fetchall()
                self.assertEqual(days,[(d['date'],d['revenue_cents']) for d in s['top_days']])
                self.assertEqual(db.execute('SELECT COUNT(DISTINCT canonical_user_id) FROM users WHERE store=?',(store,)).fetchone()[0],s['unique_users'])
                self.assertEqual(db.execute('SELECT COUNT(DISTINCT author_set_key) FROM books WHERE store=?',(store,)).fetchone()[0],s['unique_author_sets'])
                best=db.execute('SELECT canonical_user_id,SUM(paid_price_cents) amount FROM orders WHERE store=? GROUP BY canonical_user_id ORDER BY amount DESC,canonical_user_id LIMIT 1',(store,)).fetchone()
                self.assertEqual(best,(s['top_customers'][0]['canonical_user_id'],s['top_customers'][0]['total_spent_cents']))
                popular=db.execute('SELECT SUM(o.quantity) amount FROM orders o JOIN books b ON o.store=b.store AND o.book_id=b.id WHERE o.store=? GROUP BY b.author_set_key ORDER BY amount DESC LIMIT 1',(store,)).fetchone()[0]
                self.assertEqual(popular,s['most_popular_author_sets'][0]['books_sold'])
    def test_no_unreported_data_loss(self):
        payload=json.loads((BASE/'results/dashboard_data.json').read_text(encoding='utf-8'))
        for s in payload['stores']:
            a=s['audit'];self.assertEqual(a['orders_input_rows'],a['orders_valid_rows']+a['orders_exact_duplicates_removed']+a['orders_quarantined'])
            self.assertEqual(sum(d['revenue_cents'] for d in s['daily_revenue']),s['total_revenue_cents'])
            self.assertEqual(a['identity_unresolved_candidate_pairs'],0)
            self.assertLess(a['date_max'],'2026-10-19')
    def test_web_exports_match_calculations(self):
        self.assertEqual((BASE/'web/data.json').read_bytes(),(BASE/'results/dashboard_data.json').read_bytes())

if __name__=='__main__':unittest.main()
