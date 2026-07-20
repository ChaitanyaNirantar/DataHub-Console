# DataHub Console

A full-stack dataset onboarding + research console, built to match a
Data Science Intern posting centered on **dataset management, data
sourcing/scraping, cataloguing, agentic development, and FastAPI**.
One backend, one frontend, three things a researcher would actually do:

1. **Browse the catalog** — what's in this dataset, what shape is it,
   when was it last refreshed.
2. **Ask it questions in plain English** — an agent translates the
   question into a read-only SQL query, runs it, and shows both the
   query and the results.
3. **Filter and browse rows directly** — for when you just want a table.

Everything here is real and tested against a live GitHub API pull —
not mocked data.

## Stack

- **Backend**: FastAPI, single `app.py` exposing `/api/*` and serving
  the static frontend from the same process.
- **Frontend**: no build step — plain HTML/CSS/JS, fetch-based,
  designed around the "index card catalog" metaphor since the product
  itself *is* a data catalog.
- **Data**: SQLite, populated by a small ingestion pipeline that
  scrapes the GitHub Search API, validates/cleans records, and
  generates a catalog entry.
- **Agent**: an LLM translates natural language into SQL, executed
  through a read-only, SELECT-only guard. Defaults to **Gemini**
  (Google AI Studio's Flash models are free to use — no card, no
  paid tier needed); Claude is supported as a drop-in alternative.

## Project layout

```
datahub-console/
├── backend/
│   ├── schema.py        # canonical field definitions
│   ├── scraper.py        # sources data from the GitHub API
│   ├── clean.py           # validates + cleans records
│   ├── db.py               # SQLite storage (read/write)
│   ├── agent_db.py          # SQLite storage (read-only, for the agent)
│   ├── catalog.py            # generates catalog.json / catalog.md
│   ├── agent_gemini.py         # NL -> SQL agent (Gemini, default, free)
│   ├── agent.py                  # NL -> SQL agent (Claude, optional)
│   ├── run_pipeline.py             # CLI: scrape -> clean -> load -> catalog
│   └── app.py                        # FastAPI app: API + serves frontend
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── data/                          # generated: datahub.db, catalog files
└── requirements.txt
```

## Run it

```bash
pip install -r requirements.txt

# Get a free key at https://aistudio.google.com/apikey (no card needed)
export GEMINI_API_KEY=your-key-here   # only needed for the "Ask" panel

# 1. Onboard the dataset (creates data/datahub.db + catalog files)
python backend/run_pipeline.py --query "topic:machine-learning language:python" --pages 2

# 2. Run the console
cd backend
uvicorn app:app --reload --port 8000
```

Open **http://127.0.0.1:8000** — the catalog card, the ask console,
and the filterable browser all load from that one URL.

If you skip step 1, the app still runs; the catalog card will say so
and the browse table will be empty until you onboard a dataset. If you
skip the API key, everything still runs too — only the "Ask" panel
will show a message telling you to set one.

### Switching LLM providers

The agent is swappable with one env var:

```bash
export LLM_PROVIDER=gemini   # default — free tier via Google AI Studio
export LLM_PROVIDER=claude   # requires ANTHROPIC_API_KEY instead
```

Both providers implement the same `QueryAgent.ask(question) -> dict`
interface (`agent_gemini.py` / `agent.py`), so `app.py` never has to
know which one is active.

## API reference

| Method | Path | What it does |
|---|---|---|
| GET | `/api/health` | status + row count |
| GET | `/api/datasets` | list onboarded datasets |
| GET | `/api/datasets/{name}/catalog` | full catalog entry (fields, null rates, freshness) |
| GET | `/api/datasets/github_repos/languages` | distinct languages, for the filter dropdown |
| GET | `/api/datasets/github_repos/query?language=&min_stars=&limit=` | filtered rows |
| POST | `/api/ask` | `{"question": "..."}` → generated SQL + results |

## Design notes

- **Schema in one place** (`schema.py`) keeps cleaning, validation,
  and cataloging from drifting apart.
- **Quarantine, not silent drop**: rejected records keep their reason.
- **Agent safety is structural, not a prompt promise**: the agent's
  DB connection is opened `mode=ro`, and every generated query is
  checked against a SELECT-only, single-statement allowlist before
  it's allowed to run.
- **Frontend concept**: the catalog is presented as index cards with
  a drawer-label tab — a literal nod to "cataloguing," which is the
  core responsibility in the job description, rather than a generic
  admin-dashboard look.
