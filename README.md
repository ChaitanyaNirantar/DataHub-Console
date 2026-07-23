A full-stack dataset onboarding + research console — source data from an external API, clean and catalog it, then browse it or ask questions about it in plain English.

Built to mirror a real "Data Science Intern — DataHub" role: dataset management, data sourcing/scraping, cataloguing, an internal API, and agentic (LLM-powered) query tooling. One backend, one frontend, no mocked data.

Table of Contents
What it does
Why it exists
Stack
Project layout
Getting started
API reference
Switching LLM providers
Design decisions
Limitations
Author
What it does

Three things a researcher would actually want to do with a dataset:

Browse the catalog — what's in this dataset, what shape is it, when was it last refreshed. Field-level types and null rates, generated from the real data, not hand-written.
Ask it questions in plain English — an LLM agent translates the question into a read-only SQL query, runs it, and shows both the generated query and the results.
Filter and browse rows directly — for when you just want a table, no AI in the loop.

The data is real: every run pulls live repository metadata from the public GitHub Search API — stars, forks, language, license, issue counts — validates and cleans it, and loads it into SQLite.

Why it exists

Most portfolio projects for a "data platform" role are either a static Jupyter notebook or a CRUD app with fake data. This one tries to actually exercise the responsibilities such a role involves:

Responsibility	Where it lives
Data sourcing & scraping	backend/scraper.py
Data preparation / validation	backend/clean.py
Dataset management (storage)	backend/db.py
Data cataloguing	backend/catalog.py
Internal API development	backend/app.py (FastAPI)
Agentic development	backend/agent_gemini.py, backend/agent_db.py
Data consulting (self-service)	frontend/
Stack
Backend — FastAPI. A single app.py exposes /api/* and serves the static frontend from the same process — one process, one port, nothing extra to run.
Frontend — plain HTML/CSS/JS, no build step, fetch-based. Designed around an "index card catalog" metaphor since the product itself is a data catalog, rather than a generic admin-dashboard look.
Data — SQLite, populated by a small ingestion pipeline that scrapes the GitHub Search API, validates/cleans records, and generates a catalog entry (JSON + Markdown).
Agent — an LLM translates natural language into SQL, executed through a read-only, SELECT-only guard. Defaults to Gemini (Google AI Studio's Flash models are free — no card, no paid tier); Claude is supported as a drop-in alternative behind the same interface.
Project layout
datahub-console/
├── backend/
│   ├── schema.py          # canonical field definitions — single source of truth
│   ├── scraper.py         # sources data from the GitHub API
│   ├── clean.py           # validates + cleans records, quarantines the rest
│   ├── db.py               # SQLite storage (read/write, idempotent upsert)
│   ├── agent_db.py          # SQLite storage (read-only, SELECT-only guard)
│   ├── catalog.py            # generates catalog.json / catalog.md
│   ├── agent_gemini.py        # NL → SQL agent (Gemini, default, free)
│   ├── agent.py                 # NL → SQL agent (Claude, optional)
│   ├── run_pipeline.py           # CLI: scrape → clean → load → catalog
│   └── app.py                     # FastAPI app: API + serves the frontend
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── data/                        # generated at runtime: datahub.db, catalog files
└── requirements.txt
Getting started
bash
pip install -r requirements.txt

# Get a free key at https://aistudio.google.com/apikey (no card needed)
export GEMINI_API_KEY=your-key-here    # only needed for the "Ask" panel

# 1. Onboard the dataset (creates data/datahub.db + catalog files)
python backend/run_pipeline.py --query "topic:machine-learning language:python" --pages 2

# 2. Run the console
cd backend
uvicorn app:app --reload --port 8000

Open http://127.0.0.1:8000 — the catalog card, the ask console, and the filterable browser all load from that one URL.

Skip step 1 and the app still runs — the catalog card explains itself, and the browse table is empty until you onboard a dataset.
Skip the API key and the app still runs too — only the "Ask" panel shows a message telling you to set one; catalog browsing and filtering work with zero configuration.

Windows (PowerShell) users: use $env:GEMINI_API_KEY = "your-key-here" instead of export, and python -m venv venv / .\venv\Scripts\Activate.ps1 if working in a virtual environment.

API reference
Method	Path	What it does
GET	/api/health	status + row count
GET	/api/datasets	list onboarded datasets
GET	/api/datasets/{name}/catalog	full catalog entry (fields, null rates, freshness)
GET	/api/datasets/github_repos/languages	distinct languages, for the filter dropdown
GET	/api/datasets/github_repos/query?language=&min_stars=&limit=	filtered rows
POST	/api/ask	{"question": "..."} → generated SQL + results
Switching LLM providers

The agent is swappable with one environment variable — no code changes needed:

bash
export LLM_PROVIDER=gemini   # default — free tier via Google AI Studio
export LLM_PROVIDER=claude   # requires ANTHROPIC_API_KEY instead

Both providers implement the identical QueryAgent.ask(question) -> dict interface (agent_gemini.py / agent.py), so app.py never has to know which one is active.

Design decisions
Schema in one place (schema.py) — cleaning, validation, and cataloging all read from the same field spec, so they can't silently drift out of sync with each other.
Quarantine, not silent drop — rejected records are kept with a reason attached, so a bad pipeline run is visible and auditable instead of just producing a quietly-smaller dataset.
Idempotent upserts — re-running the pipeline refreshes existing rows (INSERT ... ON CONFLICT ... DO UPDATE) instead of duplicating or erroring, so it's safe to schedule.
Catalog is computed, not hand-written — row counts and null rates come from the actual clean data every time, so the catalog can't lie about the dataset.
Agent safety is structural, not a prompt promise — the agent's database connection is opened mode=ro at the SQLite level, and every generated query is checked against a SELECT-only, single-statement guard before it's allowed to run. The model plans; a deterministic guard executes.
Lazy agent construction — a missing API key degrades only the /api/ask endpoint (clean 503), not the entire service.
No frontend build step — matches the scope of the project: one process to run, nothing to compile.
Limitations

Being upfront about what this is and isn't:

No authentication — this is a local/demo tool, not something to expose publicly as-is.
SQLite, not Postgres — fine for a single dataset and a demo; the storage layer (db.py) is intentionally thin so swapping databases later is contained to one file.
The SELECT-only guard is a string check, not a real SQL parser — it catches the obvious attack surface but a production version should validate the AST (e.g. via sqlglot) rather than scan for keywords.
No automated test suite yet — verified by hand against the live GitHub API and by mocking the LLM call to test the surrounding logic.
Only one dataset (github_repos) is wired up end-to-end; onboarding a second would mean adding another scraper plus a generic (rather than hardcoded) query endpoint.
Author

Chaitanya Rajesh Nirantar — M.S. Information Science, University of Illinois Urbana-Champaign GitHub · LinkedIn · cn32@illinois.edu
