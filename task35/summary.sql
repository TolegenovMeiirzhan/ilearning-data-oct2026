INSERT INTO summary (publication_year, book_count, average_price)
WITH yearly_totals AS (
    SELECT publication_year,
           COUNT(*) AS book_count,
           SUM(price_usd_mills) AS sum_mills
    FROM books
    GROUP BY publication_year
), rounded AS (
    SELECT publication_year,
           book_count,
           (sum_mills + 5 * book_count) / (10 * book_count) AS average_cents
    FROM yearly_totals
)
SELECT publication_year,
       book_count,
       printf('%d.%02d', average_cents / 100, average_cents % 100)
FROM rounded
ORDER BY publication_year;
