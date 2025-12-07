from sqlalchemy import select, or_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import Book
from schemas import BookCreate
from typing import List, Optional

async def get_books(db: AsyncSession, q: str = "") -> List[Book]:
    stmt = select(Book) if not q else select(Book).where(or_(
        Book.title.ilike(f"%{q}%"), Book.author.ilike(f"%{q}%"),
        Book.isbn13 == q, Book.isbn10 == q, Book.lccn == q
    ))
    result = await db.execute(stmt)
    return result.scalars().all()

async def create_book(db: AsyncSession, book: BookCreate) -> Optional[Book]:
    db_book = Book(**book.dict())
    db.add(db_book)
    await db.commit()
    await db.refresh(db_book)
    return db_book

async def get_book(db: AsyncSession, book_id: int) -> Optional[Book]:
    result = await db.execute(select(Book).where(Book.id == book_id))
    return result.scalar_one_or_none()

async def update_book(db: AsyncSession, book_id: int, book: BookCreate):
    await db.execute(update(Book).where(Book.id == book_id).values(**book.dict(exclude_unset=True)))
    await db.commit()

async def delete_book(db: AsyncSession, book_id: int):
    await db.execute(delete(Book).where(Book.id == book_id))
    await db.commit()

