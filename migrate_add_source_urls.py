from sqlalchemy import create_engine, inspect, text

DATABASE_URL = "sqlite:///./books.db"
engine = create_engine(DATABASE_URL)

inspector = inspect(engine)

columns_to_add = [
    ("openlibrary_source_url", "TEXT"),
    ("googlebooks_source_url", "TEXT")
]

for col_name, col_type in columns_to_add:
    if 'books' in inspector.get_table_names() and 'cover_url' not in [c['name'] for c in inspector.get_columns('books')]:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE books ADD COLUMN {col_name} {col_type}"))
        print(f"Added column {col_name}")
    else:
        print("No change needed.")
