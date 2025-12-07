# main.py — FINAL, WORKING version with absolute imports and fixed Google lookup
from fastapi import FastAPI, Form, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

# Absolute imports — no dots
from database import init_db, get_db
from crud.book import get_books, create_book, get_book, update_book, delete_book
from services.google_books import lookup  # ← this is the function
from schemas import BookCreate

app = FastAPI(title="BookTracker")
templates = Jinja2Templates(directory="templates")

app.add_event_handler("startup", init_db)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, q: str = "", db: AsyncSession = Depends(get_db)):
    books = await get_books(db, q)
    return templates.TemplateResponse("home.html", {"request": request, "books": books, "q": q})

@app.get("/add", response_class=HTMLResponse)
async def add_form(request: Request):
    return templates.TemplateResponse("add.html", {"request": request})

@app.post("/add")
async def add_book(
    title: str = Form(""),
    author: str = Form(""),
    isbn: str = Form(""),
    lccn: str = Form(""),
    use_lookup: bool = Form(True),   # ← renamed from "lookup" to avoid conflict
    db: AsyncSession = Depends(get_db)
):
    book_data = {
        "title": title.strip() or "Untitled",
        "author": author.strip() or "Unknown",
        "lccn": lccn.strip() or None,
        "isbn13": None,
        "isbn10": None,
        "description": None,
        "cover_url": None
    }

    if use_lookup and isbn.strip():
        gdata = await lookup(isbn=isbn.strip())  # ← now correctly calls the function
        if gdata:
            book_data.update({
                "title": gdata["title"],
                "author": gdata["author"],
                "isbn13": gdata["isbn13"],
                "isbn10": gdata["isbn10"],
                "description": gdata["description"],
                "cover_url": gdata["cover_url"]
            })

    await create_book(db, BookCreate(**book_data))
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
    db: AsyncSession = Depends(get_db)
):
    book_data = BookCreate(
        title=title,
        author=author,
        isbn13=isbn13 or None,
        isbn10=isbn10 or None,
        lccn=lccn or None
    )
    await update_book(db, book_id, book_data)
    return RedirectResponse("/", status_code=303)

@app.get("/delete/{book_id}")
async def delete_book_route(book_id: int, db: AsyncSession = Depends(get_db)):
    await delete_book(db, book_id)
    return RedirectResponse("/", status_code=303)

