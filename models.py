# models.py
from sqlalchemy import Column, Integer, String, Numeric, Date
from database import Base   # ← absolute, correct

class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    isbn13 = Column(String, unique=True, index=True)
    isbn10 = Column(String, unique=True, index=True)
    lccn = Column(String, unique=True, index=True)
    description = Column(String)
    cover_url = Column(String)
    copies = Column(Integer, default=1, nullable=False)
    purchase_price = Column(Numeric(10, 2), nullable=True)
    date_purchased = Column(Date, nullable=True)
    date_read = Column(Date, nullable=True)
    comment = Column(String, nullable=True)
    daw_book_number = Column(Integer, nullable=True)
    daw_catalog_number = Column(String(6), nullable=True)
    publication_date = Column(Date, nullable=True)
    publisher = Column(String(255), nullable=True)
    pages = Column(Integer, nullable=True)
    dimensions = Column(String(50), nullable=True)
    book_format = Column(String(100), nullable=True)

