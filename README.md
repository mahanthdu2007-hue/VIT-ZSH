# PRISM Engine

Career decision-support platform for Indian students (Class 9–12 and college) and their
parents. It combines student psychometrics, family financial constraints and labour-market
data into ranked, explainable career pathways. Built for the DataQuest 3.0 final round.

**Live demo:** https://YOUR-HF-USERNAME-prism-engine.hf.space
(hosted free on [Hugging Face Spaces](https://huggingface.co/spaces/YOUR-HF-USERNAME/prism-engine);
the first visit after a quiet spell can take about a minute while the Space wakes up).

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

## Deploy for free (Hugging Face Spaces)

The app ships as one Docker container: FastAPI serves both the API and the built React
site on port 7860. Hugging Face Spaces runs it free (2 CPUs, 16 GB RAM, enough for the
System 1 and embedding models). Every push to `main` redeploys automatically through
[.github/workflows/deploy-hf.yml](.github/workflows/deploy-hf.yml).

One-time setup:

1. Create a free account at https://huggingface.co.
2. Create a Space: https://huggingface.co/new-space → name `prism-engine` → SDK **Docker**
   → template **Blank** → hardware **CPU basic (free)** → **Public** → *Create Space*.
3. Create a token: https://huggingface.co/settings/tokens → *Create new token* →
   type **Write** → copy it.
4. In this GitHub repo: *Settings → Secrets and variables → Actions*:
   - *Secrets* tab → *New repository secret* → name `HF_TOKEN`, value = the token.
   - *Variables* tab → *New repository variable* → name `HF_SPACE`,
     value = `your-hf-username/prism-engine`.
5. *Actions* tab → *Deploy to Hugging Face* → *Run workflow*. The first build takes
   about 10–15 minutes (it downloads the models). Then open
   `https://your-hf-username-prism-engine.hf.space`.

Optional: to get LLM-written explanations, add `GEMINI_API_KEY` (and `GEMINI_MODEL`) or
`NVIDIA_API_KEY` (and `NVIDIA_MODEL`) under the Space's *Settings → Variables and secrets*.
Without keys the app uses its built-in templates, and all numbers are unchanged.

To test the container locally: `docker build -t prism . && docker run -p 7860:7860 prism`.
