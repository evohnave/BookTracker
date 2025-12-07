# app.py — BookTracker with excellent Google Books lookup
from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, select, or_
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
    cover_url   = Column(String)          # ← NEW: we now save the cover!

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

app = FastAPI()

@app.on_event("startup")
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ─────────────────────── SMART GOOGLE BOOKS LOOKUP ───────────────────────
async def google_lookup(title: str = "", author: str = "", isbn: str = "") -> dict | None:
    """Returns dict with title, author, isbn13, isbn10, description, cover_url or None"""
    if not (title or author or isbn):
        return None

    async with httpx.AsyncClient(timeout=12.0) as client:
        # Prefer ISBN → exact match
        if isbn:
            url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        else:
            # Build a precise query: title in quotes + author
            q = f'intitle:"{title}"' + (f' inauthor:"{author}"' if author else "")
            url = f"https://www.googleapis.com/books/v1/volumes?q={q}&maxResults=5"

        try:
            r = await client.get(url)
            if r.status_code != 200 or not r.json().get("items"):
                return None

            # Pick the best result (first one is usually perfect)
            item = r.json()["items"][0]["volumeInfo"]

            # Extract data
            data = {
                "title": item.get("title", title),
                "author": ", ".join(item.get("authors", [author or "Unknown"])),
                "description": item.get("description", ""),
                "cover_url": item.get("imageLinks", {}).get("thumbnail", "")
                                .replace("http://", "https://") if item.get("imageLinks") else "",
                "isbn13": "",
                "isbn10": ""
            }

            # Grab ISBNs
            for ident in item.get("industryIdentifiers", []):
                if ident["type"] == "ISBN_13":
                    data["isbn13"] = ident["identifier"]
                elif ident["type"] == "ISBN_10":
                    data["isbn10"] = ident["identifier"]

            return data
        except:
            return None

# ─────────────────────── ROUTES ───────────────────────
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

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html><head><title>BookTracker</title>
    <style>
      body {{font-family: system-ui; margin:40px; line-height:1.5;}}
      input, button {{padding:8px 12px; font-size:16px;}}
      img {{max-height:120px; margin-right:15px; vertical-align:top; border-radius:6px;}}
      li {{margin:15px 0; display:flex; align-items:center;}}
      a button {{margin-left:20px;}}
    </style></head><body>
    <h1>My Books ({len(books)})</h1>
    <form><input name="q" value="{q}" placeholder="Search title/author/ISBN/LCCN" size="60">
    <button type="submit">Search</button></form>
    <a href="/add"><button>Add Book</button></a><hr>
    {"<p>No books yet.</p>" if not books else "<ul>" + "".join(
        f'<li><img src="{b.cover_url or '/static/no-cover.png'}"> '
        f'<strong>{b.title}</strong> — {b.author} '
        f'{"(ISBN-13: "+b.isbn13+")" if b.isbn13 else ""} '
        f'{"(ISBN-10: "+b.isbn10+")" if b.isbn10 else ""}</li>'
        for b in books
    ) + "</ul>"}
    </body></html>
    """)

@app.get("/add", response_class=HTMLResponse)
async def add_form(request: Request):
    return HTMLResponse("""
    <html><head><title>Add Book</title></head><body style="font-family:system-ui;margin:40px">
    <h1>Add a Book</h1>
    <form method="post">
        <p>Title:   <input name="title" size="70"></p>
        <p>Author:  <input name="author" size="70"></p>
        <p>ISBN (10 or 13): <input name="isbn" size="20"></p>
        <p>LCCN:    <input name="lccn" size="20"></p>
        <p><label><input type="checkbox" name="lookup" checked>
           Auto-fill everything from Google Books (highly recommended)</label></p>
        <button type="submit" style="padding:10px 20px;font-size:16px">Save Book</button>
        <a href="/">Cancel</a>
    </form>
    </body></html>
    """)

@app.post("/add")
async def add_book(
    title: str = Form(""),
    author: str = Form(""),
    isbn: str = Form(""),
    lccn: str = Form(""),
    lookup: bool = Form(True),
    db: AsyncSession = Depends(get_db),
):
    # If user wants lookup, go get the data from Google
    if lookup:
        data = await google_lookup(title=title, author=author, isbn=isbn.strip())
        if data:
            title = data["title"]
            author = data["author"]
            isbn13 = data["isbn13"]
            isbn10 = data["isbn10"]
            description = data["description"]
            cover_url = data["cover_url"]
        else:
            isbn13 = isbn10 = description = cover_url = None
    else:
        isbn13 = isbn10 = description = cover_url = None

    book = Book(
        title=title or "Untitled",
        author=author or "Unknown",
        isbn13=isbn13,
        isbn10=isbn10,
        lccn=lccn or None,
        description=description,
        cover_url=cover_url,
    )
    db.add(book)
    await db.commit()
    return RedirectResponse("/", status_code=303)

