"""
One-time migration: SQLite (mybooks.db) → PostgreSQL (booktrackerdb)

Usage:
    uv run --with psycopg2-binary migrate_to_postgres.py
"""

import sqlite3
import psycopg2

SQLITE_PATH = "./books.db"
PG_PARAMS = dict(
    host="localhost",
    port=30432,
    dbname="booktrackerdb",
    user="booktrackerAdmin",
    password="booktrackeradmin",
)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS books (
    id              SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    author          TEXT NOT NULL,
    isbn13          TEXT UNIQUE,
    isbn10          TEXT UNIQUE,
    lccn            TEXT UNIQUE,
    description     TEXT,
    cover_url       TEXT,
    copies          INTEGER NOT NULL DEFAULT 1,
    purchase_price  NUMERIC(10, 2),
    date_purchased  DATE,
    date_read       DATE,
    comment         TEXT,
    daw_book_number INTEGER,
    daw_catalog_number VARCHAR(6),
    publication_date DATE,
    publisher       VARCHAR(255),
    pages           INTEGER,
    dimensions      VARCHAR(50),
    book_format     VARCHAR(100)
);
"""

COLUMNS = [
    "title", "author", "isbn13", "isbn10", "lccn", "description",
    "cover_url", "copies", "purchase_price", "date_purchased", "date_read",
    "comment", "daw_book_number", "daw_catalog_number", "publication_date",
    "publisher", "pages", "dimensions", "book_format",
]

INSERT_SQL = f"""
INSERT INTO books ({', '.join(COLUMNS)})
VALUES ({', '.join(f'%s' for _ in COLUMNS)})
ON CONFLICT DO NOTHING
"""


def main():
    # --- Read from SQLite ---
    src = sqlite3.connect(SQLITE_PATH)
    src.row_factory = sqlite3.Row
    rows = src.execute("SELECT * FROM books").fetchall()
    src.close()
    print(f"Read {len(rows)} books from {SQLITE_PATH}")

    # --- Write to PostgreSQL ---
    dst = psycopg2.connect(**PG_PARAMS)
    cur = dst.cursor()

    cur.execute(CREATE_TABLE)
    dst.commit()

    inserted = 0
    for row in rows:
        values = tuple(row[col] for col in COLUMNS)
        cur.execute(INSERT_SQL, values)
        if cur.rowcount:
            inserted += 1

    # Reset the sequence to the max existing id
    cur.execute("SELECT setval('books_id_seq', COALESCE((SELECT MAX(id) FROM books), 1))")
    dst.commit()

    cur.close()
    dst.close()
    print(f"Inserted {inserted} books into PostgreSQL ({len(rows) - inserted} skipped as duplicates)")


if __name__ == "__main__":
    main()
