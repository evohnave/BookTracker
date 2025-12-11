# services/google_books.py — FINAL, BULLETPROOF VERSION
import httpx
from typing import Tuple, Optional, Dict

async def google_lookup(isbn: str = "") -> Tuple[Optional[Dict], str]:
    if not isbn:
        return None, ""
    async with httpx.AsyncClient(timeout=6.0) as client:
        try:
            r = await client.get(f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}")
            if r.status_code == 200 and r.json().get("items"):
                i = r.json()["items"][0]["volumeInfo"]
                return {
                    "title": i.get("title", ""),
                    "author": ", ".join(i.get("authors", ["Unknown"])),
                    "description": i.get("description", ""),
                    "cover_url": i.get("imageLinks", {}).get("thumbnail", "").replace("http://", "https://"),
                    "isbn13": next((x["identifier"] for x in i.get("industryIdentifiers", []) if x["type"] == "ISBN_13"), ""),
                    "isbn10": next((x["identifier"] for x in i.get("industryIdentifiers", []) if x["type"] == "ISBN_10"), ""),
                }, "Google Books"
        except:
            pass
    return None, ""

async def openlibrary_lookup(isbn: str = "") -> Tuple[Optional[Dict], str]:
    if not isbn:
        return None, ""
    async with httpx.AsyncClient(timeout=6.0) as client:
        try:
            r = await client.get(f"https://openlibrary.org/isbn/{isbn}.json")
            if r.status_code != 200:
                return None, ""
            data = r.json()
            cover_id = data.get("covers", [None])[0]
            # Simple author handling — no second API call
            author_name = "Unknown"
            if data.get("by_statement"):
                author_name = data["by_statement"]
            elif data.get("authors"):
                # Sometimes author name is directly in the main record
                first_author = data["authors"][0]
                if isinstance(first_author, dict) and "name" in first_author:
                    author_name = first_author["name"]

            return {
                "title": data.get("title", ""),
                "author": author_name,
                "description": (
                    data.get("description", {}).get("value", "")
                    if isinstance(data.get("description"), dict)
                    else str(data.get("description", ""))
                ),
                "cover_url": f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None,
                "isbn13": isbn if len(isbn) == 13 else None,
                "isbn10": isbn if len(isbn) == 10 else None,
            }, "Open Library"
        except:
            return None, ""

async def isbndb_lookup(isbn: str = "") -> Tuple[Optional[Dict], str]:
    if not isbn:
        return None, ""
    async with httpx.AsyncClient(timeout=6.0) as client:
        try:
            r = await client.get(f"https://api.isbndb.com/book/{isbn}")
            if r.status_code == 200 and "book" in r.json():
                data = r.json()["book"]
                return {
                    "title": data.get("title", ""),
                    "author": ", ".join(data.get("authors", ["Unknown"])),
                    "description": data.get("synopsis", ""),
                    "cover_url": data.get("image", ""),
                    "isbn13": data.get("isbn13"),
                    "isbn10": data.get("isbn10"),
                }, "ISBNdb"
        except:
            pass
    return None, ""   # ← THIS WAS MISSING — now fixed!

# MASTER LOOKUP
async def master_lookup(isbn: str = "") -> Tuple[Optional[Dict], str]:
    result, source = await google_lookup(isbn)
    if result: return result, source

    result, source = await openlibrary_lookup(isbn)
    if result: return result, source

    result, source = await isbndb_lookup(isbn)
    if result: return result, source

    return None, "Not found in any source"

