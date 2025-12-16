import sqlite3

con = sqlite3.connect('./books.db')
cur = con.cursor()

# Add each column if it doesn't exist (SQLite ALTER TABLE adds one at a time)
columns_to_add = [
    ("daw_book_number", "INTEGER"),
    ("daw_catalog_number", "TEXT"),
    ("publication_date", "DATE"),
    ("publisher", "TEXT"),
    ("pages", "INTEGER"),
    ("dimensions", "TEXT"),
    ("book_format", "TEXT")
]

for col_name, col_type in columns_to_add:
    try:
        cur.execute(f"ALTER TABLE books ADD COLUMN {col_name} {col_type}")
        print(f"Added column {col_name}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column {col_name} already exists")
        else:
            raise

con.commit()
con.close()
print("Migration complete!")

