# PRISM Engine

Career decision-support platform for Indian students (Class 9–12 and college) and their
parents. It combines student psychometrics, family financial constraints and labour-market
data into ranked, explainable career pathways. Built for the DataQuest 3.0 final round.

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
