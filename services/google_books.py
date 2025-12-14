# services/google_books.py — FINAL: triple fallback with redirects + ISBNdb
import httpx
from typing import Tuple, Optional, Dict

async def google_lookup(isbn: str = "") -> Tuple[Optional[Dict], str]:
    if not isbn:
        return None, ""
    async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
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
    async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
        try:
            r = await client.get(f"https://openlibrary.org/isbn/{isbn}.json")
            if r.status_code != 200:
                return None, ""
            data = r.json()
            cover_id = data.get("covers", [None])[0]

            # Robust author handling
            author = "Unknown"
            if data.get("by_statement"):
                author = data["by_statement"]
            elif data.get("contributors"):
                author = ", ".join([c.get("name", "Unknown") for c in data["contributors"]])

            description = ""
            if data.get("description"):
                if isinstance(data["description"], dict):
                    description = data["description"].get("value", "")
                else:
                    description = str(data["description"])

            return {
                "title": data.get("title", ""),
                "author": author,
                "description": description,
                "cover_url": f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None,
                "isbn13": isbn if len(isbn) == 13 else None,
                "isbn10": isbn if len(isbn) == 10 else None,
            }, "Open Library"
        except:
            return None, ""

async def isbndb_lookup(isbn: str = "") -> Tuple[Optional[Dict], str]:
    if not isbn:
        return None, ""
    async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
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
    return None, ""

# MASTER LOOKUP — Open Library first (best for niche books)
async def master_lookup(isbn: str = "") -> Tuple[Optional[Dict], str]:
    result, source = await openlibrary_lookup(isbn)
    if result and result.get("title"):
        return result, source

    result, source = await google_lookup(isbn)
    if result and result.get("title"):
        return result, source

    result, source = await isbndb_lookup(isbn)
    if result and result.get("title"):
        return result, source

    return None, "No book found"

