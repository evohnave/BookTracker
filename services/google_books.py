import httpx
from typing import Dict, Optional, List

async def lookup(title: str = "", author: str = "", isbn: str = "") -> Optional[Dict]:
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

async def general_lookup(title: str = "", author: str = "", isbn: str = "", lccn: str = "") -> List[Dict]:
    if not (title or author or isbn or lccn):
        return []
    async with httpx.AsyncClient(timeout=12) as client:
        q = ""
        if isbn:
            q += f"isbn:{isbn}"
        if lccn:
            q += f" lccn:{lccn}"
        if title:
            q += f' intitle:"{title}"'
        if author:
            q += f' inauthor:"{author}"'
        url = f"https://www.googleapis.com/books/v1/volumes?q={q.strip()}&maxResults=5"
        try:
            r = await client.get(url)
            if r.status_code != 200 or not r.json().get("items"):
                return []
            results = []
            for item in r.json()["items"]:
                i = item["volumeInfo"]
                results.append({
                    "title": i.get("title", ""),
                    "author": ", ".join(i.get("authors", [])),
                    "description": i.get("description", ""),
                    "cover_url": i.get("imageLinks", {}).get("thumbnail", "").replace("http://", "https://"),
                    "isbn13": next((x["identifier"] for x in i.get("industryIdentifiers", []) if x["type"] == "ISBN_13"), ""),
                    "isbn10": next((x["identifier"] for x in i.get("industryIdentifiers", []) if x["type"] == "ISBN_10"), ""),
                })
            return results
        except Exception:
            return []

