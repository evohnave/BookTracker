# crud/book.py — ABSOLUTE IMPORTS, with copy counting
from sqlalchemy import select, or_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book
from schemas import BookCreate
from typing import List, Optional

async def get_books(db: AsyncSession, q: str = "") -> List[Book]:
    stmt = select(Book) if not q else select(Book).where(or_(
        Book.title.ilike(f"%{q}%"),
        Book.author.ilike(f"%{q}%"),
        Book.isbn13 == q,
        Book.isbn10 == q,
        Book.lccn == q
    ))
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_book(db: AsyncSession, book_id: int) -> Optional[Book]:
    result = await db.execute(select(Book).where(Book.id == book_id))
    return result.scalar_one_or_none()

async def find_book_by_isbn(db: AsyncSession, isbn13: str = None, isbn10: str = None) -> Optional[Book]:
    if isbn13:
        result = await db.execute(select(Book).where(Book.isbn13 == isbn13))
    elif isbn10:
        result = await db.execute(select(Book).where(Book.isbn10 == isbn10))
    else:
        return None
    return result.scalar_one_or_none()

async def add_copy_or_create(db: AsyncSession, book_data: BookCreate) -> Book:
    """Add a copy if book exists by ISBN, otherwise create new"""
    existing = await find_book_by_isbn(db, book_data.isbn13, book_data.isbn10)

    if existing:
        existing.copies += 1
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        new_book = Book(**book_data.model_dump(exclude_unset=True))
        new_book.copies = 1
        db.add(new_book)
        await db.commit()
        await db.refresh(new_book)
        return new_book

async def update_book(db: AsyncSession, book_id: int, book_data: BookCreate):
    await db.execute(
        update(Book)
        .where(Book.id == book_id)
        .values(**book_data.model_dump(exclude_unset=True))
    )
    await db.commit()

async def delete_book(db: AsyncSession, book_id: int):
    await db.execute(delete(Book).where(Book.id == book_id))
    await db.commit()

