#!/usr/bin/env python3
"""
One-time CLI script to download all book cover images to local storage
and populate the local_cover_path column for existing database entries.

Usage:
    python download_covers.py [--force]

Options:
    --force     Re-download even if a local copy already exists.
"""
import asyncio
import shutil
import sys
from pathlib import Path

import httpx
from sqlalchemy import select, update

# Ensure project root is on the path when run directly
sys.path.insert(0, str(Path(__file__).parent))

from database import AsyncSessionLocal, init_db
from models import Book
from services.cover_cache import (
    COVERS_DIR,
    NO_COVER_SRC,
    local_cover_filepath,
    local_cover_url,
)


async def download_single(client: httpx.AsyncClient, url: str, dest: Path) -> bool:
    try:
        resp = await client.get(url, follow_redirects=True, timeout=15)
        if resp.status_code == 200 and len(resp.content) > 0:
            dest.write_bytes(resp.content)
            return True
    except Exception as e:
        print(f"    Error: {e}")
    return False


async def main(force: bool = False) -> None:
    await init_db()
    COVERS_DIR.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Book))
        books = result.scalars().all()

    print(f"Found {len(books)} books.\n")

    updated = 0
    skipped = 0
    failed = 0

    async with httpx.AsyncClient() as client:
        for book in books:
            dest = local_cover_filepath(book.isbn13, book.lccn)
            url_path = local_cover_url(book.isbn13, book.lccn)

            if dest is None:
                print(f"  SKIP  [{book.id}] {book.title!r} — no isbn13 or lccn identifier")
                skipped += 1
                continue

            if dest.exists() and not force:
                # Still make sure local_cover_path is set in DB
                if book.local_cover_path != url_path:
                    async with AsyncSessionLocal() as db:
                        await db.execute(
                            update(Book).where(Book.id == book.id).values(local_cover_path=url_path)
                        )
                        await db.commit()
                print(f"  EXIST [{book.id}] {book.title!r} — already cached, db updated if needed")
                skipped += 1
                continue

            print(f"  DL    [{book.id}] {book.title!r} → {dest.name}")

            success = False
            if book.cover_url:
                success = await download_single(client, book.cover_url, dest)
                if not success:
                    print(f"    Download failed, using placeholder")

            if not success:
                shutil.copy(NO_COVER_SRC, dest)

            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Book).where(Book.id == book.id).values(local_cover_path=url_path)
                )
                await db.commit()

            if success:
                updated += 1
            else:
                failed += 1

    print(f"\nDone. Downloaded: {updated}  Placeholder: {failed}  Skipped: {skipped}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    asyncio.run(main(force=force))
