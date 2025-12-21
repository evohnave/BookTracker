from pydantic import BaseModel
from typing import Optional

class BookBase(BaseModel):
    title: str
    author: str
    isbn13: Optional[str] = None
    isbn10: Optional[str] = None
    lccn: Optional[str] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None

class BookCreate(BookBase):
    pass

class Book(BookBase):
    id: int

    class Config:
        from_attributes = True
