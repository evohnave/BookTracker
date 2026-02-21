from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import date

class BookBase(BaseModel):
    title: str
    author: str
    isbn13: Optional[str] = None
    isbn10: Optional[str] = None
    lccn: Optional[str] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None

class BookCreate(BookBase):
    copies: Optional[int] = None
    purchase_price: Optional[Decimal] = None
    date_purchased: Optional[date] = None
    date_read: Optional[date] = None
    comment: Optional[str] = None

class Book(BookBase):
    id: int

    class Config:
        from_attributes = True

