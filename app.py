# app.py — FINAL, FULLY WORKING BookTracker (Edit + Delete + Covers + Google Lookup)
from fastapi import FastAPI, Form, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, select, or_, update, delete, text
from sqlalchemy.ext.declarative import declarative_base
import httpx

DATABASE_URL = "sqlite+aiosqlite:///./books.db"
engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class Book(Base):
    __tablename__ = "books"
    id          = Column(Integer, primary_key=True)
    title       = Column(String, nullable=False, index=True)
    author      = Column(String, nullable=False, index=True)
    isbn13      = Column(String, unique=True, index=True)
    isbn10      = Column(String, unique=True, index=True)
    lccn        = Column(String, unique=True, index=True)
    description = Column(String)
    cover_url   = Column(String)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

app = FastAPI()

@app.on_event("startup")
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        result = await conn.execute(text("PRAGMA table_info(books);"))
        columns = [row[1] for row in result.fetchall()]
        if "cover_url" not in columns:
            await conn.execute(text("ALTER TABLE books ADD COLUMN cover_url TEXT"))
            await conn.commit()

async def google_lookup(title="", author="", isbn=""):
    if not (title or author or isbn):
        return None
    async with httpx.AsyncClient(timeout=12) as client:
        if isbn:
            url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        else:
            q = f'intitle:"{title}"' + (f' inauthor:"{author}"' if author else "")
            url = f"https://www.googleapis.com/books/v1/volumes?q={q}&maxResults=5"
        try:
            r = await client.get(url)
            if r.status_code != 200 or not r.json().get("items"):
                return None
            i = r.json()["items"][0]["volumeInfo"]
            return {
                "title": i.get("title", title),
                "author": ", ".join(i.get("authors", [author or "Unknown"])),
                "description": i.get("description", ""),
                "cover_url": i.get("imageLinks", {}).get("thumbnail", "").replace("http://", "https://"),
                "isbn13": next((x["identifier"] for x in i.get("industryIdentifiers", []) if x["type"] == "ISBN_13"), ""),
                "isbn10": next((x["identifier"] for x in i.get("industryIdentifiers", []) if x["type"] == "ISBN_10"), ""),
            }
        except Exception:
            return None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, q: str = "", db: AsyncSession = Depends(get_db)):
    stmt = select(Book) if not q else select(Book).where(or_(
        Book.title.ilike(f"%{q}%"), Book.author.ilike(f"%{q}%"),
        Book.isbn13 == q, Book.isbn10 == q, Book.lccn == q
    ))
    books = (await db.execute(stmt)).scalars().all()

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>BookTracker</title>
        <style>
            body {{font-family:system-ui;margin:40px;background:#f9f9f9;line-height:1.6;}}
            input,button {{padding:10px 16px;font-size:16px;border-radius:6px;border:1px solid #ccc;}}
            img {{max-height:140px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);}}
            li {{background:white;padding:16px;margin:12px 0;border-radius:10px;display:flex;align-items:center;}}
            .actions button {{margin-left:8px;padding:6px 12px;font-size:14px;}}
            a button {{background:#0066cc;color:white;border:none;}}
        </style>
    </head>
    <body>
        <h1>My Books ({len(books)})</h1>
        <form>
            <input name="q" value="{q}" placeholder="Search title/author/ISBN/LCCN" size="60">
            <button type="submit">Search</button>
        </form>
        <a href="/add"><button>Add Book</button></a><hr>
        {"<p>No books yet.</p>" if not books else "<ul style='list-style:none;padding:0'>" + "".join(
            f'<li><img src="{b.cover_url or "https://via.placeholder.com/100x150.png?text=No+Cover"}">'
            f'<div style="margin-left:20px">'
            f'<strong style="font-size:1.3em">{b.title}</strong><br>{b.author}<br>'
            f'<small>{"ISBN-13: "+b.isbn13+" " if b.isbn13 else ""}'
            f'{"ISBN-10: "+b.isbn10+" " if b.isbn10 else ""}'
            f'{"LCCN: "+b.lccn if b.lccn else ""}</small><br>'
            f'<div class="actions">'
            f'<a href="/edit/{b.id}"><button>Edit</button></a> '
            f'<a href="/delete/{b.id}" onclick="return confirm(\'Really delete {b.title}?\')"><button style="background:#c33;color:white">Delete</button></a>'
            f'</div></div></li>'
            for b in books
        ) + "</ul>"}
    </body>
    </html>
    """)

@app.get("/add", response_class=HTMLResponse)
async def add_form(request: Request):
    return HTMLResponse("""
    <html><head><title>Add Book</title><style>body{font-family:system-ui;margin:40px}</style></head><body>
    <h1>Add a Book</h1>
    <form method="post">
        <p>Title:   <input name="title" size="70"></p>
        <p>Author:  <input name="author" size="70"></p>
        <p>ISBN (10 or 13): <input name="isbn" size="20"></p>
        <p>LCCN:    <input name="lccn" size="20"></p>
        <p><label><input type="checkbox" name="lookup" checked> Auto-fill from Google Books</label></p>
        <button type="submit">Save Book</button> <a href="/">Cancel</a>
    </form></body></html>
    """)

@app.post("/add")
async def add_book(
    title: str = Form(""), author: str = Form(""), isbn: str = Form(""),
    lccn: str = Form(""), lookup: bool = Form(True), db: AsyncSession = Depends(get_db)
):
    isbn13 = isbn10 = description = cover_url = None
    if lookup:
        data = await google_lookup(title=title, author=author, isbn=isbn)
        if data:
            title = data["title"]
            author = data["author"]
            isbn13 = data["isbn13"]
            isbn10 = data["isbn10"]
            description = data["description"]
            cover_url = data["cover_url"]

    db.add(Book(
        title=title or "Untitled",
        author=author or "Unknown",
        isbn13=isbn13,
        isbn10=isbn10,
        lccn=lccn or None,
        description=description,
        cover_url=cover_url
    ))
    await db.commit()
    return RedirectResponse("/", status_code=303)

@app.get("/edit/{book_id}", response_class=HTMLResponse)
async def edit_form(book_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    book = (await db.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if not book:
        raise HTTPException(404)
    return HTMLResponse(f"""
    <html><head><title>Edit Book</title><style>body{{font-family:system-ui;margin:40px}}</style></head><body>
    <h1>Edit Book</h1>
    <form method="post">
        <p>Title:   <input name="title" value="{book.title}" size="70"></p>
        <p>Author:  <input name="author" value="{book.author}" size="70"></p>
        <p>ISBN-13: <input name="isbn13" value="{book.isbn13 or ''}" size="20"></p>
        <p>ISBN-10: <input name="isbn10" value="{book.isbn10 or ''}" size="20"></p>
        <p>LCCN:    <input name="lccn" value="{book.lccn or ''}" size="20"></p>
        <button type="submit">Update</button> <a href="/">Cancel</a>
    </form>
    </body></html>
    """)

@app.post("/edit/{book_id}")
async def update_book(book_id: int, title: str = Form(...), author: str = Form(...),
                      isbn13: str = Form(""), isbn10: str = Form(""), lccn: str = Form(""),
                      db: AsyncSession = Depends(get_db)):
    await db.execute(update(Book).where(Book.id == book_id).values(
        title=title, author=author, isbn13=isbn13 or None,
        isbn10=isbn10 or None, lccn=lccn or None
    ))
    await db.commit()
    return RedirectResponse("/", status_code=303)

@app.get("/delete/{book_id}")
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Book).where(Book.id == book_id))
    await db.commit()
    return RedirectResponse("/", status_code=303)

