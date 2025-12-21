from sqlalchemy import create_engine, inspect, text

DATABASE_URL = "sqlite:///./books.db"
engine = create_engine(DATABASE_URL)

inspector = inspect(engine)

columns_to_add = [
    ("openlibrary_source_url", "TEXT"),
    ("googlebooks_source_url", "TEXT")
]

for col_name, col_type in columns_to_add:
    with engine.connect() as conn:
        conn.execute(text(f"ALTER TABLE books ADD COLUMN {col_name} {col_type}"))
        print(f"Added column {col_name}")
