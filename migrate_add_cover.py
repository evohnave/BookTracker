# migrate.py – one-time script to add cover_url column
from sqlalchemy import create_engine, inspect, text

DATABASE_URL = "sqlite:///./books.db"
engine = create_engine(DATABASE_URL)

inspector = inspect(engine)
if 'books' in inspector.get_table_names() and 'cover_url' not in [c['name'] for c in inspector.get_columns('books')]:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE books ADD COLUMN cover_url TEXT"))
    print("Added cover_url column!")
else:
    print("No change needed.")
