# Website Crawler & Chunking Backend

No API keys. No Redis. No paid services. Runs entirely locally with SQLite.

## Files
- `main.py` — FastAPI app, the entry point
- `crawler.py` — BeautifulSoup + Playwright crawlers (strategy pattern)
- `chunker.py` — Recursive Character Splitter + LangChain splitter
- `storage.py` — SQLite storage (auto-creates `crawler.db`, no setup needed)
- `requirements.txt` — dependencies

## Setup (run in Antigravity's terminal)

```bash
# 1. Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright's browser (only needed if you plan to use the
#    'playwright' crawler engine for JS-heavy sites)
playwright install chromium

# 4. Run the server
uvicorn main:app --reload --port 8000
```

Server will be live at `http://localhost:8000`. Visit `http://localhost:8000/docs`
for interactive Swagger UI where you can test every endpoint without writing code.

## Quick test (once running)

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "crawler_engine": "beautifulsoup",
    "chunker_strategy": "recursive",
    "max_depth": 1,
    "max_pages": 5
  }'
```

This returns a `job_id`. Then check progress:

```bash
curl http://localhost:8000/api/jobs/<job_id>
curl http://localhost:8000/api/jobs/<job_id>/chunks
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/jobs` | Start a crawl+chunk job |
| GET | `/api/jobs` | List all jobs |
| GET | `/api/jobs/{id}` | Check job status |
| GET | `/api/jobs/{id}/pages` | List crawled pages |
| GET | `/api/jobs/{id}/chunks` | List resulting chunks |

## Next steps
1. Confirm this works locally first (see Quick test above)
2. Use `ngrok http 8000` to get a temporary public URL
3. Point your Lovable frontend's API calls at that URL
4. Once everything works end-to-end, deploy to Render (free tier) for a permanent URL
