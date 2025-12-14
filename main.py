# main.py — FINAL, WORKING with triple lookup + proper error handling
from fastapi import FastAPI, Form, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, update, delete, text
from database import init_db, get_db
from crud.book import get_books, add_copy_or_create, get_book, update_book, delete_book
from services.google_books import master_lookup as lookup  # ← This is the magic one
from schemas import BookCreate
from models import Book

app = FastAPI(title="BookTracker")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_event_handler("startup", init_db)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, q: str = "", db: AsyncSession = Depends(get_db)):
    books = await get_books(db, q)
    return templates.TemplateResponse("home.html", {"request": request, "books": books, "q": q})

@app.get("/add", response_class=HTMLResponse)
async def add_form(request: Request):
    return templates.TemplateResponse("add.html", {
        "request": request,
        "query": {"title": "", "author": "", "isbn": "", "lccn": ""}
    })

@app.post("/lookup", response_class=HTMLResponse)
async def lookup_books(
    title: str = Form(""),
    author: str = Form(""),
    isbn: str = Form(""),
    lccn: str = Form(""),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    result, source = await lookup(isbn=isbn.strip())

    if not result:
        return templates.TemplateResponse("add.html", {
            "request": request,
            "query": {"title": title, "author": author, "isbn": isbn, "lccn": lccn},
            "error": f"ISBN {isbn or 'unknown'} not found in any source — add manually below"
        })

    return templates.TemplateResponse("lookup.html", {
        "request": request,
        "results": [result],
        "source": source,
        "query": {"title": title, "author": author, "isbn": isbn, "lccn": lccn}
    })

@app.post("/add_selected")
async def add_selected(
    title: str = Form(...),
    author: str = Form(...),
    isbn13: str = Form(""),
    isbn10: str = Form(""),
    lccn: str = Form(""),
    description: str = Form(""),
    cover_url: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    book_data = BookCreate(
        title=title,
        author=author,
        isbn13=isbn13 or None,
        isbn10=isbn10 or None,
        lccn=lccn or None,
        description=description or None,
        cover_url=cover_url or None
    )
    result_book = await add_copy_or_create(db, book_data)

    if result_book.copies > 1:
        return HTMLResponse(f"""
        <h2>Added Another Copy!</h2>
        <p>You now have <strong>{result_book.copies} copies</strong> of <em>{title}</em> by {author}</p>
        <a href="/">Back to Library</a>
        """)

    return RedirectResponse("/", status_code=303)

@app.get("/edit/{book_id}", response_class=HTMLResponse)
async def edit_form(book_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    book = await get_book(db, book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    return templates.TemplateResponse("edit.html", {"request": request, "book": book})

@app.post("/edit/{book_id}")
async def update_book_route(
    book_id: int,
    title: str = Form(...),
    author: str = Form(...),
    isbn13: str = Form(""),
    isbn10: str = Form(""),
    lccn: str = Form(""),
    copies: int = Form(1),
    cover_url: str = Form(""),
    purchase_price: str = Form(""),
    date_purchased: str = Form(""),
    date_read: str = Form(""),
    comment: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    from decimal import Decimal
    from datetime import date

    price = Decimal(purchase_price) if purchase_price else None
    purchased = date.fromisoformat(date_purchased) if date_purchased else None
    read = date.fromisoformat(date_read) if date_read else None

    book_data = {
        "title": title,
        "author": author,
        "isbn13": isbn13 or None,
        "isbn10": isbn10 or None,
        "lccn": lccn or None,
        "copies": max(1, copies),
        "cover_url": cover_url or None,
        "purchase_price": price,
        "date_purchased": purchased,
        "date_read": read,
        "comment": comment or None
    }
    await db.execute(update(Book).where(Book.id == book_id).values(**book_data))
    await db.commit()
    return RedirectResponse("/", status_code=303)

@app.get("/delete/{book_id}")
async def delete_book_route(book_id: int, db: AsyncSession = Depends(get_db)):
    await delete_book(db, book_id)
    return RedirectResponse("/", status_code=303)

