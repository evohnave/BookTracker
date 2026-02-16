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

CREATE_FAKE_ISBN13 = """
CREATE TABLE IF NOT EXISTS fake_isbn13 (
    registrant_publication INTEGER PRIMARY KEY,
    isbn13 TEXT GENERATED ALWAYS AS (
        '978611' || lpad(registrant_publication::text, 6, '0') ||
        CASE
            WHEN (
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 1, 1))::int * 1 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 2, 1))::int * 3 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 3, 1))::int * 1 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 4, 1))::int * 3 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 5, 1))::int * 1 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 6, 1))::int * 3 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 7, 1))::int * 1 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 8, 1))::int * 3 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 9, 1))::int * 1 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 10, 1))::int * 3 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 11, 1))::int * 1 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 12, 1))::int * 3
            ) % 10 = 0 THEN '0'
            ELSE (10 - (
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 1, 1))::int * 1 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 2, 1))::int * 3 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 3, 1))::int * 1 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 4, 1))::int * 3 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 5, 1))::int * 1 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 6, 1))::int * 3 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 7, 1))::int * 1 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 8, 1))::int * 3 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 9, 1))::int * 1 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 10, 1))::int * 3 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 11, 1))::int * 1 +
                (SUBSTR('978611' || lpad(registrant_publication::text, 6, '0'), 12, 1))::int * 3
            ) % 10)::text
        END
    ) STORED
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
    fake_rows = src.execute("SELECT registrant_publication FROM fake_isbn13").fetchall()
    src.close()
    print(f"Read {len(rows)} books and {len(fake_rows)} fake_isbn13 rows from {SQLITE_PATH}")

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

    # --- Migrate fake_isbn13 ---
    cur.execute(CREATE_FAKE_ISBN13)
    fake_inserted = 0
    for row in fake_rows:
        cur.execute(
            "INSERT INTO fake_isbn13 (registrant_publication) VALUES (%s) ON CONFLICT DO NOTHING",
            (row["registrant_publication"],),
        )
        if cur.rowcount:
            fake_inserted += 1

    dst.commit()
    print(f"Inserted {fake_inserted} fake_isbn13 rows ({len(fake_rows) - fake_inserted} skipped as duplicates)")

    cur.close()
    dst.close()
    print(f"Inserted {inserted} books into PostgreSQL ({len(rows) - inserted} skipped as duplicates)")


if __name__ == "__main__":
    main()
