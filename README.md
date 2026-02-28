# BookTracker

A personal book collection manager built with FastAPI and PostgreSQL, deployed on Kubernetes.

## Features

- **Add books** via ISBN/title/author lookup (queries Google Books, Open Library, and ISBNdb in parallel) or manual entry
- **Edit and delete** books from your collection
- **Track copies** — adding a duplicate ISBN increments the copy count instead of creating a duplicate
- **Rich metadata** — title, author, ISBNs, LCCN, publisher, publication date, page count, format, dimensions, cover image, DAW catalog numbers
- **Personal info** — purchase price, date purchased, date read, notes
- **Sort and filter** by title, author, date read, date purchased, publisher, or format
- **Fake ISBN-13 generator** for books without real ISBNs (prefix `978611`)

## Tech Stack

- **Backend:** Python 3.13, FastAPI, SQLAlchemy (async), asyncpg
- **Database:** PostgreSQL
- **Frontend:** Jinja2 templates, HTML/CSS
- **External APIs:** Google Books, Open Library, ISBNdb
- **Deployment:** Docker (multi-stage), Kubernetes

## Project Structure

```
BookTracker/
├── main.py               # FastAPI routes
├── models.py             # SQLAlchemy ORM models
├── schemas.py            # Pydantic schemas
├── database.py           # DB engine and session setup
├── crud/
│   └── book.py           # CRUD operations
├── services/
│   ├── google_books.py   # External API lookups
│   └── isbn_utils.py     # ISBN validation and conversion
├── templates/            # Jinja2 HTML templates
├── static/               # CSS, images
├── k8s/                  # Kubernetes manifests
├── Dockerfile
├── deploy.sh
└── teardown.sh
```

## Local Development

**Prerequisites:** PostgreSQL running on port 30432, [uv](https://github.com/astral-sh/uv) installed.

```bash
uv sync
uv run uvicorn main:app --reload
```

The app expects:
```
DATABASE_URL=postgresql+asyncpg://booktrackerAdmin:booktrackeradmin@localhost:30432/booktrackerdb
```

## Deployment (Kubernetes)

```bash
./deploy.sh     # Build Docker image and apply k8s manifests
./teardown.sh   # Remove k8s resources (leaves namespace intact)
```

The app is served at **http://localhost:30090** via a NodePort service.

## Database

The `books` table stores all book and collection data. A separate `fake_isbn13` table holds auto-generated ISBN-13 values (prefix `978611`) for books that lack a real ISBN, generated via the `POST /next_fake_isbn13` endpoint.

### Migrating from SQLite

A one-time migration script is included for importing legacy data:

```bash
uv run --with psycopg2-binary migrate_to_postgres.py
```

## Version

Current version: **1.1.1**
