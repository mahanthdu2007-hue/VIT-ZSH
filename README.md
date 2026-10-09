# PRISM Engine

Career decision-support platform for Indian students (Class 9–12 and college) and their
parents. It combines student psychometrics, family financial constraints and labour-market
data into ranked, explainable career pathways. Built for the DataQuest 3.0 final round.

**Live demo:** https://prism-engine.onrender.com
(hosted free on [Render](https://render.com); after 15 idle minutes the server sleeps, so the
first visit can take about a minute to wake it up).

The full specification is in [CLAUDE.md](CLAUDE.md). Progress is tracked in
[docs/PROGRESS.md](docs/PROGRESS.md).

## What you need

- Python 3.11
- Node.js 20 or newer
- Git

## One-time setup

1. Copy the settings file: `cp .env.example .env` (Windows: `copy .env.example .env`).
   The defaults work offline with no API keys.
2. Backend:
   ```bash
   cd backend
   python3.11 -m venv .venv            # Windows: py -3.11 -m venv .venv
   source .venv/bin/activate           # Windows: .venv\Scripts\activate
   pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
   pip install -r requirements.txt
   ```
3. Frontend:
   ```bash
   cd frontend
   npm install
   ```

## Run

Start both servers together:

- macOS/Linux: `./dev.sh`
- Windows: `powershell -ExecutionPolicy Bypass -File dev.ps1`

Then open http://localhost:5173. The API runs at http://localhost:8000
(interactive docs at http://localhost:8000/docs).

## Checks

```bash
cd backend && pytest -q                                    # backend tests
cd frontend && npm run typecheck && npm run build          # frontend checks
```

## Regenerate API types

After changing the backend API:

```bash
cd backend && python scripts/export_openapi.py   # writes frontend/openapi.json
cd frontend && npm run gen:api                   # writes src/api/schema.d.ts
```

## Deploy for free (Render)

The app ships as one Docker container: FastAPI serves both the API and the built React
site. It runs on Render's free web service in **lite mode**: no ML models are installed
([backend/requirements-lite.txt](backend/requirements-lite.txt)), System 1 uses the keyword
backend, and explanations are retrieved from the dataset instead of Chroma. Every score,
cost and ranking uses exactly the same formulas as the full install. It uses about 140 MB
of memory, well inside the free 512 MB.

One-time setup:

1. Sign in at https://dashboard.render.com with GitHub.
2. *New → Blueprint* → connect this repository → Render reads [render.yaml](render.yaml)
   → *Apply*. The first build takes about 5 minutes.
3. Open `https://prism-engine.onrender.com` (Render shows the exact address on the
   service page). Every push to `main` redeploys automatically.

Optional: to get LLM-written explanations and chat replies, set `GEMINI_API_KEY` and
`GEMINI_MODEL` in the service's *Environment* tab. Without them the app uses its built-in
templates, and all numbers are unchanged.

To test the container locally: `docker build -t prism . && docker run -p 10000:10000 prism`.
