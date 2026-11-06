# FinSight AI - Agentic Financial Research Copilot

An analyst asks a question in natural language; the agent answers **with evidence** by combining:

| Need | Tool | Where |
|---|---|---|
| "What happened" (numbers) | 5 reviewed SQL functions | SQL Server 2022 |
| "Why / what does the company say" | Semantic search over 10-K filings | ChromaDB + sentence-transformers |
| Math (returns, Sharpe, drawdown, beta, portfolio) | Deterministic pandas/NumPy code | `quant_tools.py` |

The LLM **never writes SQL and never computes a number it can look up or calculate.**
100% free and local: SQL Server (Docker), ChromaDB (embedded), sentence-transformers, Ollama, LangGraph, FastAPI, Streamlit.

## Architecture
```
yfinance ──> validate ──> MERGE upserts ──> SQL Server ──> SQL Tool ─┐
SEC EDGAR ─> clean XBRL -> chunk -> embed -> ChromaDB  ──> RAG Tool ──┼─> LangGraph agent (Ollama) -> FastAPI (+audit log) -> Streamlit
                                              prices/DB ──> Quant tools ┘
```
Scope: 44 US companies, 4 per GICS sector (11 sectors).

## Project layout
```
finsight/
  config.py              settings from .env (URL.create, 127.0.0.1)
  db/                    schema.sql, init_db.py, engine.py, helpers.py (MERGE upsert, NaN guard)
  ingestion/             universe, companies, prices, fundamentals, ratios, edgar, embed
  tools/                 sql_tool.py, rag_tool.py, quant_tools.py
  agent/                 tools.py (LangChain wrappers), graph.py (LangGraph + Ollama)
  api/main.py            FastAPI: /ask /audit /health
  cli.py                 python -m finsight.cli <command>
ui/app.py                Streamlit chat
scripts/                 daily_refresh.bat, schedule_task.bat, run_all.bat
tests/                   unit tests (no DB or network needed)
Dockerfile, docker-compose.yml
```

## Option A - Local run (Windows/macOS/Linux)

**Prerequisites:** Python 3.10+, Docker Desktop, [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server), [Ollama](https://ollama.com).

```bash
# 1. Python env
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 2. Config (set a strong SA password + your email for SEC User-Agent)
copy .env.example .env            # macOS/Linux: cp .env.example .env

# 3. SQL Server only (from docker-compose)
docker compose up -d sqlserver

# 4. Local LLM (free). Needs ~5 GB RAM for the 7B model
ollama pull qwen2.5:7b            # lighter option: qwen2.5:3b (set OLLAMA_MODEL in .env)

# 5. Build the data layer (first run: ~15-30 min, mostly embeddings + EDGAR)
python -m finsight.cli all
#   or step by step: init-db, companies, prices, fundamentals, ratios, filings, index
#   quick test on 3 companies: python -m finsight.cli prices --tickers AAPL JPM XOM

# 6. Run
scripts\run_all.bat               # API on :8000, UI on :8501
# or: uvicorn finsight.api.main:app --port 8000   +   streamlit run ui/app.py
```
CLI test without UI: `python -m finsight.cli ask --question "Why did AAPL revenue change?"`

**Daily refresh (Windows Task Scheduler):** run `scripts\schedule_task.bat` once. It runs `finsight.cli refresh` (incremental prices + ratios) every day at 22:30.

## Option B - One-command Docker Compose
```bash
copy .env.example .env
docker compose up -d --build
docker compose exec ollama ollama pull qwen2.5:7b
docker compose run --rm api python -m finsight.cli all     # builds data (first time)
```
UI: http://localhost:8501 - API docs: http://localhost:8000/docs

## Tests
`pytest` runs 12 unit tests covering NaN guards, empty-year handling, ratio logic, chunking/overlap, XBRL cleaning and quant maths. No database, network or LLM needed.

## Design decisions (interview notes)
- **Two stores**: exact numbers in SQL, meaning-based retrieval in a vector store.
- **No LLM-written SQL**: fixed, parameterized, testable functions.
- **Idempotent**: every load is a `MERGE`; unique constraints; re-run anytime.
- **Ratios in their own table**: derived data, recompute on formula fixes; missing input => NULL, never fabricated.
- **Per-ticker try/except** and boundary validation so one bad record never stops the other 43.
- **Resumable embedding** with retries (ChromaDB + antivirus file-lock lesson). On Windows, add a Defender exclusion for `data/chroma` if you see compaction errors.
- **Local LLM caveat**: small models call tools less reliably than frontier models, hence explicit tool descriptions and a strict system prompt. Use a bigger model (`qwen2.5:14b`, `llama3.1:8b`) if your hardware allows.

## Known limitations (kept honest, as in the project summary)
- `current_ratio` is not computed (schema stores total, not current, assets/liabilities).
- yfinance lacks total liabilities for some tickers (e.g. NVDA): ROE and debt/equity are NULL there by design. Only 4 fiscal years are available.
- Beta uses an equal-weighted average of the 44 stocks as the market proxy (no paid index feed).
- Only the latest 10-K per company is indexed (no year-over-year text comparison yet).
- XOM resolves through a documented legacy-CIK override; NaN guards apply to all tickers' fundamentals.
- Research support only. Not investment advice.
