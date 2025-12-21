# main.py — FINAL, WORKING with triple lookup + proper error handling
from fastapi import FastAPI, Form, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, update, delete, text, asc, desc, case
from database import init_db, get_db
from crud.book import get_books, add_copy_or_create, get_book, update_book, delete_book
from services.google_books import (
    openlibrary_lookup, google_lookup, isbndb_lookup,
    merge_results
    )
from schemas import BookCreate
from models import Book
from services.isbn_utils import is_valid, to_isbn10, to_isbn13

app = FastAPI(title="BookTracker")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_event_handler("startup", init_db)

@app.get("/")
async def home(
    request: Request,
    db: AsyncSession = Depends(get_db),
    sort: str = "title_asc",          # default sort
    format: str | None = None,        # filter by format
    publisher: str | None = None,     # filter by publisher
    date_read_from: str | None = None,
    date_read_to: str | None = None,
    date_purchased_from: str | None = None,
    date_purchased_to: str | None = None,
):
    # Build the query
    query = select(Book)

    # Apply filters
    if format:
        query = query.where(Book.book_format.ilike(f"%{format}%"))  # partial match ok for now
    if publisher:
        query = query.where(Book.publisher.ilike(f"%{publisher}%"))

    if date_read_from:
        query = query.where(Book.date_read >= date_read_from)
    if date_read_to:
        query = query.where(Book.date_read <= date_read_to)

    if date_purchased_from:
        query = query.where(Book.date_purchased >= date_purchased_from)
    if date_purchased_to:
        query = query.where(Book.date_purchased <= date_purchased_to)

    # Apply sorting
    sort_column = Book.title  # default
    direction_func = asc

    match sort:
        case "title_asc":
            sort_column = Book.title
            direction_func = asc
        case "title_desc":
            sort_column = Book.title
            direction_func = desc
        case "author_asc":
            sort_column = Book.author
            direction_func = asc
        case "author_desc":
            sort_column = Book.author
            direction_func = desc
        case "date_read_asc":
            sort_column = Book.date_read
            direction_func = asc
        case "date_read_desc":
            sort_column = Book.date_read
            direction_func = desc
        case "date_purchased_asc":
            sort_column = Book.date_purchased
            direction_func = asc
        case "date_purchased_desc":
            sort_column = Book.date_purchased
            direction_func = desc
        case "publisher_asc":
            sort_column = Book.publisher
            direction_func = asc
        case "publisher_desc":
            sort_column = Book.publisher
            direction_func = desc
        case "format_asc":
            sort_column = Book.book_format
            direction_func = asc
        case "format_desc":
            sort_column = Book.book_format
            direction_func = desc
        case _:
            sort_column = Book.title
            direction_func = asc

    # SQLite-compatible: NULLs last using CASE
    nulls_last = case(
        (sort_column.is_(None), 1),
        else_=0
    )

    if direction_func == desc:
        # For descending: sort column descending first, then nulls (which get 1 → come last)
        sort_expr = desc(sort_column), nulls_last
    else:
        # For ascending: sort column ascending first, then nulls (which get 1 → come last)
        sort_expr = sort_column, nulls_last

    query = query.order_by(*sort_expr)

    result = await db.execute(query)
    books = result.scalars().all()

    return templates.TemplateResponse("home.html", {
        "request": request,
        "books": books,
        "current_sort": sort,
        "current_format": format,
        "current_publisher": publisher,
        "date_read_from": date_read_from,
        "date_read_to": date_read_to,
        "date_purchased_from": date_purchased_from,
        "date_purchased_to": date_purchased_to,
    })

@app.get("/add", response_class=HTMLResponse)
async def add_form(request: Request):
    return templates.TemplateResponse("add.html", {
        "request": request,
        "query": {"title": "", "author": "", "isbn": "", "lccn": ""}
    })

@app.post("/add")
async def add_book(
    title: str = Form(""),
    author: str = Form(""),
    isbn: str = Form(""),
    lccn: str = Form(""),
    lookup: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    # Validate ISBN if provided
    if isbn.strip():
        try:
            cleaned_isbn = is_valid(isbn)  # your function — raises ValueError if invalid
        except ValueError as e:
            return templates.TemplateResponse("add.html", {
                "request": request,
                "query": {"title": title, "author": author, "isbn": isbn, "lccn": lccn},
                "error": str(e)  # shows "Invalid ISBN — please check and try again"
            })
    else:
        cleaned_isbn = ""

    # Proceed with lookup if requested and valid
    if lookup and cleaned_isbn:
        gdata = await lookup(isbn=cleaned_isbn)
        if gdata:
            title = gdata["title"]
            author = gdata["author"]
            isbn13 = gdata["isbn13"]
            isbn10 = gdata["isbn10"]
            description = gdata["description"]
            cover_url = gdata["cover_url"]
        else:
            isbn13 = isbn10 = description = cover_url = None
    else:
        isbn13 = isbn10 = description = cover_url = None

    # Derive missing format
    if cleaned_isbn:
        if len(cleaned_isbn) == 13 and not isbn10:
            isbn10 = to_isbn10(cleaned_isbn)
        elif len(cleaned_isbn) == 10 and not isbn13:
            isbn13 = to_isbn13(cleaned_isbn)

    book_data = BookCreate(
        title=title or "Untitled",
        author=author or "Unknown",
        isbn13=isbn13,
        isbn10=isbn10,
        lccn=lccn or None,
        description=description,
        cover_url=cover_url
    )
    await add_copy_or_create(db, book_data)
    return RedirectResponse("/", status_code=303)

@app.post("/lookup", response_class=HTMLResponse)
async def lookup_books(
    title: str = Form(""),
    author: str = Form(""),
    isbn: str = Form(""),
    lccn: str = Form(""),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    from asyncio import gather

    # Run all three lookups in parallel
    openlib, google, isbndb = await gather(
        openlibrary_lookup(isbn=isbn.strip()),
        google_lookup(isbn=isbn.strip()),
        isbndb_lookup(isbn=isbn.strip())
    )

    # Merge for the synthesis pane
    synthesis = merge_results(openlib, google, isbndb)

    return templates.TemplateResponse("lookup.html", {
        "request": request,
        "openlib": openlib or {},
        "google": google or {},
        "isbndb": isbndb or {},
        "synthesis": synthesis,
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
    # Clean and validate any provided ISBNs
    isbn13_clean = ""
    isbn10_clean = ""

    if isbn13.strip():
        cleaned = isbn13.replace("-", "").replace(" ", "")
        if is_valid(cleaned):
            isbn13_clean = cleaned

    if isbn10.strip():
        cleaned = isbn10.replace("-", "").replace(" ", "")
        if is_valid(cleaned):
            isbn10_clean = cleaned

    # Derive the other format if only one is present and valid
    if isbn13_clean and not isbn10_clean:
        derived = to_isbn10(isbn13_clean)
        if derived:
            isbn10_clean = derived

    if isbn10_clean and not isbn13_clean:
        derived = to_isbn13(isbn10_clean)
        if derived:
            isbn13_clean = derived

    book_data = BookCreate(
        title=title,
        author=author,
        isbn13=isbn13_clean or None,
        isbn10=isbn10_clean or None,
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
    # === NEW FIELDS BELOW ===
    publisher: str = Form(""),
    publication_date: str = Form(""),
    pages: str = Form(""),
    book_format: str = Form(""),
    dimensions: str = Form(""),
    daw_book_number: str = Form(""),
    daw_catalog_number: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    from decimal import Decimal
    from datetime import date

    price = Decimal(purchase_price) if purchase_price else None
    purchased = date.fromisoformat(date_purchased) if date_purchased else None
    read = date.fromisoformat(date_read) if date_read else None

    # Convert new fields with proper typing / None handling
    pub_date = date.fromisoformat(publication_date) if publication_date else None
    pages_int = int(pages) if pages else None
    daw_num = int(daw_book_number) if daw_book_number else None

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
        "comment": comment or None,
        # === NEW FIELDS ===
        "publisher": publisher or None,
        "publication_date": pub_date,
        "pages": pages_int,
        "book_format": book_format or None,
        "dimensions": dimensions or None,
        "daw_book_number": daw_num,
        "daw_catalog_number": daw_catalog_number or None,
    }
    await db.execute(update(Book).where(Book.id == book_id).values(**book_data))
    await db.commit()
    return RedirectResponse("/", status_code=303)

@app.post("/delete/{book_id}")
async def delete_book_route(book_id: int, db: AsyncSession = Depends(get_db)):
    await delete_book(db, book_id)
    return RedirectResponse("/", status_code=303)

