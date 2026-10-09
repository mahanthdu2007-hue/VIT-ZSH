<div align="center">

# PRISM Engine

**One career decision, split into five colours you can see.**

A prism splits light into a spectrum. PRISM splits a career choice into the five things
that actually decide it, and shows the student *and* the parents exactly how each one adds up.

**Live demo:** https://prism-engine-3d2t.onrender.com
(hosted free on [Render](https://render.com); after 15 idle minutes the server sleeps, so the
first visit can take about a minute to wake it up).

![Student Fit](https://img.shields.io/badge/Student_Fit-30-6C4CF1?style=flat-square)
![Financial Fit](https://img.shields.io/badge/Financial_Fit-20-0E9F8E?style=flat-square)
![Market Demand](https://img.shields.io/badge/Market_Demand-20-D9930D?style=flat-square)
![Growth](https://img.shields.io/badge/Growth-15-2F7DE1?style=flat-square)
![Parent Alignment](https://img.shields.io/badge/Parent_Alignment-15-D63F74?style=flat-square)

*Built for the DataQuest 3.0 final round.*

</div>

---

## The problem

An Indian Class 12 student picks a career with three voices in the room: their own interests,
their parents' hopes, and a budget nobody says out loud. Most career tools hear only the first.
PRISM hears all three, and puts the job market on the table too.

## What it does

- **Ranks careers out of 100**, and every score breaks into five coloured parts you can hover and read.
- **Solves the money.** A Financial Constraint Solver (`scipy.optimize.milp`) picks the best route each family can afford, counting real scholarships.
- **Never a dead end.** Careers that cost too much aren't hidden. They become *stretch options*, with scholarships, cheaper routes and similar careers.
- **Measures family disagreement.** The Parent-Student Conflict Index shows where student and parents differ, then finds a **middle path** using Nash bargaining, with what each side gains.
- **Live What-If.** "What if our budget is ₹3 lakh?" The ranking re-orders live, with a one-line reason for every move.
- **Ask PRISM.** A chatbot that answers questions about *your* results only, in plain words.
- **SWOT, skill gaps, a year-by-year plan, city demand and payback time** for every career.

## The rule we never break

> **Numbers never come from an AI.**

Every score, cost and ranking comes from Python code that gives the same answer every time.
AI is used only to read free text and to word explanations. A numeric guardrail checks every
number the AI writes against the engine's results, and replaces any sentence that fails the check.
If every AI service goes offline, PRISM still works: it falls back to templates and keyword rules.

## How it works

```
Student + Parent answers
        │
   Vectorize & Normalize ──► System 1 reads free text (zero-shot NLI)
        │
   Financial Constraint Solver (MILP) ──► Career Matcher ──► Conflict Index + Middle Path
        │
   Market Intelligence ──► PRISM Score = 30·SF + 20·FF + 20·MD + 15·G + 15·PA
        │
   Ranking · Stretch options · SWOT · Roadmap ──► System 2 explains (RAG + guardrail)
```

Every stage records its real values in a trace returned with the result. Nothing is a black box.

## Proof, not promises

Counted by `scripts/benchmark.py`, never typed by hand ([full report](docs/BENCHMARK.md)):

| | |
|---|---|
| Engine scenarios | **30 / 30** passed |
| Full-pipeline persona scenarios | **5 / 5** passed |
| Property tests | **7 / 7** passed on **7,000** random profiles |
| Dataset | **55** careers · **32** real scholarships · **30** entrance exams |

All money values are labelled *indicative estimates*.

## Run it

```bash
cp .env.example .env                                    # works offline, no API keys needed
cd backend && python -m venv .venv && .venv/Scripts/activate   # macOS/Linux: source .venv/bin/activate
pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements.txt
cd ../frontend && npm install
```

Start both servers: `./dev.sh` (macOS/Linux) or `powershell -ExecutionPolicy Bypass -File dev.ps1` (Windows).
Open **http://localhost:5173** and pick a demo family.

## Deploy for free (Render)

The app ships as one Docker container: FastAPI serves both the API and the built React
site. It runs on Render's free web service in **lite mode**: no ML models are installed
([backend/requirements-lite.txt](backend/requirements-lite.txt)), System 1 uses the keyword
backend, and explanations are retrieved from the dataset instead of Chroma. Every score,
cost and ranking uses exactly the same formulas as the full install. It uses about 140 MB
of memory, well inside the free 512 MB.

One-time setup:

1. Sign in at https://dashboard.render.com with GitHub.
2. *New → Blueprint* → paste this repository's GitHub URL under *Public Git Repository*
   → Render reads [render.yaml](render.yaml) → *Deploy Blueprint*. The first build takes about 5 minutes.
3. Open `https://prism-engine-3d2t.onrender.com` (Render shows the exact address on the
   service page). After pushing new commits, click *Manual Deploy → Deploy latest commit*
   (or connect your GitHub account in Render to redeploy on every push).

Optional: to get LLM-written explanations and chat replies, set `GEMINI_API_KEY` and
`GEMINI_MODEL` in the service's *Environment* tab. Without them the app uses its built-in
templates, and all numbers are unchanged.

To test the container locally: `docker build -t prism . && docker run -p 10000:10000 prism`.

## Built with

FastAPI · Pydantic · SciPy · NumPy · HuggingFace Transformers · ChromaDB · React · TypeScript ·
Tailwind · Framer Motion · Recharts · React Flow. Everything is free and open source.

<div align="center">

**PRISM: because the right career is the one the whole family can understand.**

</div>
