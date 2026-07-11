"""
SQLite storage layer.
No separate database service needed - creates a local file `crawler.db`.
"""
import sqlite3
import json
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager

DB_PATH = "crawler.db"


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                start_url TEXT NOT NULL,
                crawler_engine TEXT NOT NULL,
                chunker_strategy TEXT NOT NULL,
                max_depth INTEGER DEFAULT 1,
                max_pages INTEGER DEFAULT 20,
                status TEXT DEFAULT 'queued',
                error TEXT,
                created_at TEXT,
                completed_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                url TEXT NOT NULL,
                status_code INTEGER,
                clean_text TEXT,
                fetched_at TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                page_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                chunk_index INTEGER,
                content TEXT,
                metadata TEXT,
                FOREIGN KEY (page_id) REFERENCES pages(id)
            )
        """)
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# ---------- Jobs ----------

def create_job(start_url, crawler_engine, chunker_strategy, max_depth, max_pages) -> str:
    job_id = new_id()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO jobs (id, start_url, crawler_engine, chunker_strategy,
               max_depth, max_pages, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'queued', ?)""",
            (job_id, start_url, crawler_engine, chunker_strategy, max_depth, max_pages, now()),
        )
        conn.commit()
    return job_id


def update_job_status(job_id: str, status: str, error: str = None):
    with get_conn() as conn:
        if status in ("completed", "failed"):
            conn.execute(
                "UPDATE jobs SET status = ?, error = ?, completed_at = ? WHERE id = ?",
                (status, error, now(), job_id),
            )
        else:
            conn.execute(
                "UPDATE jobs SET status = ?, error = ? WHERE id = ?",
                (status, error, job_id),
            )
        conn.commit()


def get_job(job_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def list_jobs():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


# ---------- Pages ----------

def save_page(job_id: str, url: str, status_code: int, clean_text: str) -> str:
    page_id = new_id()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO pages (id, job_id, url, status_code, clean_text, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (page_id, job_id, url, status_code, clean_text, now()),
        )
        conn.commit()
    return page_id


def list_pages(job_id: str):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM pages WHERE job_id = ?", (job_id,)).fetchall()
        return [dict(r) for r in rows]


# ---------- Chunks ----------

def save_chunks(job_id: str, page_id: str, chunks: list[str], metadata: dict):
    with get_conn() as conn:
        for i, content in enumerate(chunks):
            conn.execute(
                """INSERT INTO chunks (id, page_id, job_id, chunk_index, content, metadata)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (new_id(), page_id, job_id, i, content, json.dumps(metadata)),
            )
        conn.commit()


def list_chunks(job_id: str, limit: int = 200, offset: int = 0):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM chunks WHERE job_id = ? LIMIT ? OFFSET ?",
            (job_id, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]
