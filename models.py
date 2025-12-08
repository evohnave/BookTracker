# models.py
from sqlalchemy import Column, Integer, String
from database import Base

class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    isbn13 = Column(String, unique=True, index=True)   # ISBN still unique per title
    isbn10 = Column(String, unique=True, index=True)
    lccn = Column(String, unique=True, index=True)
    description = Column(String)
    cover_url = Column(String)
    copies = Column(Integer, default=1, nullable=False)  # ← NEW: number of copies

