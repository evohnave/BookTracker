# services/google_books.py — FINAL: triple fallback with redirects + ISBNdb
import httpx
from typing import Tuple, Optional, Dict

async def google_lookup(isbn: str = "") -> Optional[Dict]:
    if not isbn:
        return None
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
                }
        except:
            pass
    return None

async def openlibrary_lookup(isbn: str = "") -> Optional[Dict]:
    if not isbn:
        return None
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            r = await client.get(f"https://openlibrary.org/isbn/{isbn}.json")
            if r.status_code != 200:
                return None
            data = r.json()
            cover_id = data.get("covers", [None])[0]

            author = "Unknown"
            if data.get("by_statement"):
                author = data["by_statement"]
            elif data.get("authors"):
                # Fetch first author's name if only key is provided
                first_author = data["authors"][0]
                if isinstance(first_author, dict) and "key" in first_author:
                    ar = await client.get(f"https://openlibrary.org{first_author['key']}.json")
                    if ar.status_code == 200:
                        author_data = ar.json()
                        author = author_data.get("name", "Unknown")
                    else:
                        author = "Unknown"
                elif isinstance(first_author, dict) and "name" in first_author:
                    author = first_author["name"]

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
            }
        except Exception as e:
            print(f"Open Library error: {e}")
            return None

async def isbndb_lookup(isbn: str = "") -> Optional[Dict]:
    if not isbn:
        return None
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
                }
        except:
            pass
    return None

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

def merge_results(openlib: Optional[Dict], google: Optional[Dict], isbndb: Optional[Dict]) -> Dict:
    sources = [r for r in [openlib, google, isbndb] if r]
    merged = {}
    for key in ["title", "author", "description", "cover_url", "isbn13", "isbn10"]:
        for r in sources:
            if r.get(key):
                merged[key] = r[key]
                break
    return merged

