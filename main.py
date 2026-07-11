"""
Website Crawler + Chunking Pipeline - FastAPI backend.

Run locally:
    uvicorn main:app --reload --port 8000

No API keys required. No Redis required. Uses local SQLite (crawler.db).
"""
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Literal

import storage
import crawler
import chunker

app = FastAPI(title="Website Crawler & Chunking Pipeline")

# CORS - allows your Lovable frontend (or any browser) to call this API.
# Tighten allow_origins to your actual Lovable domain once you have it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage.init_db()


class CreateJobRequest(BaseModel):
    start_url: HttpUrl
    crawler_engine: Literal["beautifulsoup", "playwright"] = "beautifulsoup"
    chunker_strategy: Literal["recursive", "langchain"] = "recursive"
    max_depth: int = 1
    max_pages: int = 10
    chunk_size: int = 800
    chunk_overlap: int = 100


def run_job(job_id: str, req: CreateJobRequest):
    """Runs the crawl + chunk pipeline in the background."""
    try:
        storage.update_job_status(job_id, "running")
        chunk_fn = chunker.get_chunker(req.chunker_strategy)

        for url, html, status_code, error in crawler.crawl_site(
            str(req.start_url), req.crawler_engine, req.max_depth, req.max_pages
        ):
            if error:
                continue  # skip broken pages, keep crawling the rest
            clean_text = crawler.extract_clean_text(html)
            if not clean_text.strip():
                continue

            page_id = storage.save_page(job_id, url, status_code, clean_text)
            pieces = chunk_fn.split(clean_text, req.chunk_size, req.chunk_overlap)
            storage.save_chunks(job_id, page_id, pieces, metadata={"source_url": url})

        storage.update_job_status(job_id, "completed")
    except Exception as e:
        storage.update_job_status(job_id, "failed", error=str(e))


@app.post("/api/jobs")
def create_job(req: CreateJobRequest, background_tasks: BackgroundTasks):
    job_id = storage.create_job(
        str(req.start_url), req.crawler_engine, req.chunker_strategy, req.max_depth, req.max_pages
    )
    background_tasks.add_task(run_job, job_id, req)
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/jobs")
def list_jobs():
    return storage.list_jobs()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/jobs/{job_id}/pages")
def get_pages(job_id: str):
    return storage.list_pages(job_id)


@app.get("/api/jobs/{job_id}/chunks")
def get_chunks(job_id: str, limit: int = 200, offset: int = 0):
    return storage.list_chunks(job_id, limit, offset)


@app.get("/")
def root():
    return {"status": "ok", "message": "Website Crawler API is running"}
