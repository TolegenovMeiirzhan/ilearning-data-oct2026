CREATE TABLE books (
    id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    genre TEXT NOT NULL,
    publisher TEXT NOT NULL,
    publication_year INTEGER NOT NULL,
    original_price TEXT NOT NULL,
    currency TEXT NOT NULL CHECK (currency IN ('USD', 'EUR')),
    price_usd_mills INTEGER NOT NULL CHECK (price_usd_mills >= 0)
);

CREATE TABLE summary (
    publication_year INTEGER PRIMARY KEY,
    book_count INTEGER NOT NULL CHECK (book_count > 0),
    average_price TEXT NOT NULL
);
