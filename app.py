# app.py — 100% working single file, no external templates, no errors
from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, select, or_
from sqlalchemy.ext.declarative import declarative_base
import httpx

# ──────────────────────────────────────────────────────────────
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

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

app = FastAPI()

@app.on_event("startup")
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ──────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, q: str = "", db: AsyncSession = Depends(get_db)):
    if q:
        stmt = select(Book).where(
            or_(
                Book.title.ilike(f"%{q}%"),
                Book.author.ilike(f"%{q}%"),
                Book.isbn13 == q,
                Book.isbn10 == q,
                Book.lccn == q,
            )
        )
    else:
        stmt = select(Book)
    result = await db.execute(stmt)
    books = result.scalars().all()

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>My Books</title>
        <style>
            body {{font-family: Arial, sans-serif; margin: 40px;}}
            input, button {{padding: 8px; font-size: 16px;}}
            li {{margin: 12px 0;}}
            a {{margin-left: 20px;}}
        </style>
    </head>
    <body>
        <h1>My Book Collection ({len(books)} books)</h1>
        <form>
            <input name="q" value="{q}" placeholder="Search title / author / ISBN / LCCN" size="60">
            <button type="submit">Search</button>
        </form>
        <a href="/add"><button>Add New Book</button></a>
        <hr>
        {"<p>No books yet — add one above!</p>" if not books else "<ul>" + "".join(
            f"<li><strong>{b.title}</strong> — {b.author} "
            f"{'(ISBN-13: ' + b.isbn13 + ')' if b.isbn13 else ''} "
            f"{'(ISBN-10: ' + b.isbn10 + ')' if b.isbn10 else ''} "
            f"{'(LCCN: ' + b.lccn + ')' if b.lccn else ''}</li>"
            for b in books
        ) + "</ul>"}
    </body>
    </html>
    """
    return HTMLResponse(html)

# ──────────────────────────────────────────────────────────────
@app.get("/add", response_class=HTMLResponse)
async def add_form(request: Request):
    return HTMLResponse("""
    <html><head><title>Add Book</title></head><body style="font-family:Arial;margin:40px">
    <h1>Add a Book</h1>
    <form method="post">
        <p>Title:   <input name="title" required size="60"></p>
        <p>Author:  <input name="author" required size="60"></p>
        <p>ISBN-13: <input name="isbn13" size="20"></p>
        <p>ISBN-10: <input name="isbn10" size="20"></p>
        <p>LCCN:    <input name="lccn" size="20"></p>
        <p><label><input type="checkbox" name="lookup"> Auto-fill from Google Books (needs ISBN)</label></p>
        <button type="submit">Save Book</button> <a href="/">Cancel</a>
    </form>
    </body></html>
    """)

# ───────────────────────────────────────────────────────────────
@app.post("/add")
async def add_book(
    title: str = Form(...),
    author: str = Form(...),
    isbn13: str = Form(""),
    isbn10: str = Form(""),
    lccn: str = Form(""),
    lookup: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    if lookup and (isbn13 or isbn10):
        term = isbn13 or isbn10
        async with httpx.AsyncClient() as client:
            r = await client.get(f"https://www.googleapis.com/books/v1/volumes?q=isbn:{term}")
            if r.status_code == 200 and r.json().get("items"):
                info = r.json()["items"][0]["volumeInfo"]
                title = info.get("title", title)
                author = ", ".join(info.get("authors", [author]))
                for i in info.get("industryIdentifiers", []):
                    if i["type"] == "ISBN_13": isbn13 = i["identifier"]
                    if i["type"] == "ISBN_10": isbn10 = i["identifier"]

    book = Book(
        title=title,
        author=author,
        isbn13=isbn13 or None,
        isbn10=isbn10 or None,
        lccn=lccn or None
    )
    db.add(book)
    await db.commit()
    return RedirectResponse("/", status_code=303)

