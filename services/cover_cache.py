import shutil
from pathlib import Path

import httpx
from sqlalchemy import update

COVERS_DIR = Path("static/covers")
NO_COVER_SRC = Path("static/no-cover.jpg")


def cover_identifier(isbn13: str | None, lccn: str | None) -> str | None:
    return isbn13 or lccn or None


def local_cover_url(isbn13: str | None, lccn: str | None) -> str | None:
    ident = cover_identifier(isbn13, lccn)
    return f"/static/covers/{ident}.jpg" if ident else None


def local_cover_filepath(isbn13: str | None, lccn: str | None) -> Path | None:
    ident = cover_identifier(isbn13, lccn)
    return COVERS_DIR / f"{ident}.jpg" if ident else None


async def download_and_cache_bg(
    book_id: int,
    isbn13: str | None,
    lccn: str | None,
    cover_url: str | None,
) -> None:
    """Background task: downloads cover image and updates local_cover_path in DB."""
    from database import AsyncSessionLocal
    from models import Book

    dest = local_cover_filepath(isbn13, lccn)
    url_path = local_cover_url(isbn13, lccn)
    if dest is None:
        return

    COVERS_DIR.mkdir(parents=True, exist_ok=True)

    BROWSER_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    downloaded = False
    if cover_url:
        try:
            async with httpx.AsyncClient(timeout=10, headers=BROWSER_HEADERS) as client:
                resp = await client.get(cover_url, follow_redirects=True)
                if resp.status_code == 200 and len(resp.content) > 0:
                    dest.write_bytes(resp.content)
                    downloaded = True
        except Exception:
            pass

    if not downloaded:
        if cover_url:
            # Download failed but cover_url exists — don't cache a placeholder.
            # Leave local_cover_path as None so the browser loads cover_url directly.
            url_path = None
        else:
            # No cover_url at all — store the placeholder so something shows.
            shutil.copy(NO_COVER_SRC, dest)

    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Book).where(Book.id == book_id).values(local_cover_path=url_path)
        )
        await db.commit()
