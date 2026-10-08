# PRISM Engine — instructions for Claude Code

PRISM Engine is a career decision-support platform for Indian students (school Class 9–12
and college) and their parents. It is for the DataQuest 3.0 final round, where the team
demos this prototype live and explains how it works. Part 2 below is the full
specification and the source of truth.

# PART 1: How to work on this project

## The user is a beginner. Follow these rules.
- Do every technical step yourself: create folders, virtual environments, install
  packages, run servers, run tests, fix errors, make git commits. Never ask the user to
  run a command you can run yourself.
- When the user truly must do something (install a program, paste an API key, open a
  browser page), give numbered, click-by-click steps for their operating system, then wait.
- Use simple language in messages. No jargon without a one-line explanation.
- Before writing code in a phase, print a short plan (at most 10 lines), then continue
  without waiting for approval.

## Golden rules
1. Numbers never come from an LLM. All scores, costs and rankings are deterministic
   Python (§2).
2. Do exactly what the current phase asks. Never start a later phase, add features, or
   change the spec on your own.
3. If the spec is ambiguous, choose the simplest option that satisfies it, add one line to
   docs/DECISIONS.md (date | decision | reason), and continue. Stop and ask only if a choice
   would change a formula, the data schema or the API contract.
4. Never fake success. Run the real checks and report the real output. Never skip,
   weaken or delete a test to make it pass. Fix the real cause.
5. Never present invented facts as real. Scholarships, exams and institutions must be real.
   Numeric values are labelled indicative.
6. If a fix attempt fails 3 times, stop, explain the problem simply, and propose 2 options.

## End-of-phase protocol (do this at the end of EVERY phase)
1. Run every verification command listed in the phase, plus all earlier tests.
   Fix failures until everything passes.
2. Append to docs/PROGRESS.md: phase name, date, what was built, check results, known issues.
3. Commit: `git add -A && git commit -m "Phase <id>: <name>"`.
4. Print exactly this block, filled in:
```
==============================
PHASE <id> COMPLETE
Built: <2-4 short lines>
Checks: <each check: passed/failed>
See it yourself: <simple steps, e.g. "open http://localhost:5173 and click ...", or "nothing visible yet">
Next: type /clear, then paste the prompt for Phase <next id>
==============================
```
5. Stop. Do not continue to the next phase.

## Commands (run them yourself)
Backend (from backend/, with the venv active):
- Run: `uvicorn app.main:app --reload --port 8000`
- Test: `pytest -q`  (slow model tests: `pytest -q -m slow`)
- Data check: `python scripts/validate_data.py`
- Benchmark: `python scripts/benchmark.py`
- Warm models: `python scripts/warmup.py`
- OpenAPI export: `python scripts/export_openapi.py` (writes ../frontend/openapi.json)
Frontend (from frontend/):
- Run: `npm run dev` (port 5173, proxies /api to port 8000)
- Generate API types: `npm run gen:api`
- Check: `npm run typecheck && npm run build`
Both together: `./dev.sh` (macOS/Linux) or `powershell -ExecutionPolicy Bypass -File dev.ps1` (Windows)
Long-running servers: start them in the background, check they respond, and stop them
when the phase ends.

## Code conventions
- Python: type hints everywhere; Pydantic v2 models at every API boundary; engine/
  modules are pure functions (no I/O and no globals except cached data from loader.py).
- Every weight, threshold and constant lives in backend/app/engine/config.py with a
  comment citing its § number. No magic numbers anywhere else.
- Money is stored as integer INR. Dataset salaries are in LPA; convert explicitly.
- Every engine function returns its result plus the values the PipelineTrace needs.
- TypeScript strict. API types only from the generated src/api/schema.d.ts.
- Colours, fonts and spacing only from src/theme/tokens.ts (§15).
- UI copy: sentence case, plain language, money values tagged "Indicative estimate".
- Small, focused files. No dead code, commented-out blocks or leftover TODOs.

## Never
- Never use a paid API, or localStorage.
- Never call an LLM inside backend/app/engine/ or in the What-If path. The chatbot (§17)
  may use an LLM to understand a question and word the answer, but every number it shows
  comes from the engine.
- Never hardcode demo results. The demo always runs through the real pipeline.
- Never commit .env or API keys.

# PART 2: Technical specification (source of truth)
Prompts refer to these section numbers (§1–§16).

## §1 Product
PRISM Engine is a career decision-support platform for Indian students (school Class 9–12
and college) and their parents. It combines student psychometrics, parental financial
constraints and labour-market data into ranked, explainable, financially viable career
pathways, with a student SWOT analysis and a What-If simulator.
Built for the DataQuest 3.0 final round, where we demo the prototype and explain how it works.

## §2 Principles (apply to every line of code)
1. **Numbers never come from an LLM.** Scores, costs, budgets, salaries and rankings are
   computed by deterministic Python. LLMs only classify text (System 1) or explain
   already-computed results (System 2).
2. **Everything is explainable.** Every score exposes its component breakdown. Every
   What-If change exposes a reason.
3. **Never a dead end.** Unaffordable careers move to "Stretch options with aid" with
   scholarships, cheaper pathways and adjacent careers. They are never silently removed.
4. **The demo never breaks.** Every external dependency has an offline fallback (§12).
5. **Honest data.** Values are indicative. Every career row has `sources` and `data_note`.
   The UI labels money values "Indicative estimate".
6. **Problem-statement vocabulary** in code, API and UI: Multi-Stakeholder Inputs,
   Vectorize & Normalize, Financial Constraint Solver, Parent-Student Conflict Index,
   Industry Hiring Index, Job Velocity, Economic Disruption Index, Socio-economic Mobility,
   SWOT, Hyper-local STEAM opportunities.

## §3 Stack (all free)
- Python 3.11, FastAPI, Pydantic v2, NumPy, Pandas, SciPy ≥ 1.11 (`scipy.optimize.milp`),
  SQLAlchemy + SQLite (Postgres-ready via `DATABASE_URL`). Dataset lives in JSON files;
  SQLite stores saved assessments only.
- System 1: HuggingFace `transformers` zero-shot-classification pipeline, model
  `MoritzLaurer/deberta-v3-base-zeroshot-v2.0`; light fallback
  `typeform/distilbert-base-uncased-mnli`. CPU-only PyTorch.
- System 2: ChromaDB (local persistent) + `sentence-transformers/all-MiniLM-L6-v2`
  embeddings; generator chosen by `LLM_PROVIDER`:
  - `auto` (default): at startup, test Gemini with a tiny request; if it works use it,
    else test NVIDIA NIM; if that works use it, else `none`. Report the result in /api/health.
  - `gemini`: `google-genai` SDK, key `GEMINI_API_KEY`, model from `GEMINI_MODEL`
    (a current Flash model; confirm the exact id by listing models with the key).
  - `nvidia`: NVIDIA NIM via the `openai` Python SDK with
    base_url `https://integrate.api.nvidia.com/v1`, key `NVIDIA_API_KEY`, model from
    `NVIDIA_MODEL` (Nemotron 3.5 Lightning; confirm the exact id with GET /v1/models).
    Use only the final message content, never the reasoning field; if content is empty,
    retry once with a larger max_tokens. On HTTP 429, wait and retry once.
  - `none`: deterministic templates only.
  All providers sit behind one interface in `rag/llm.py`:
  `complete_json(system, user, schema) -> dict` and `complete_text(system, user) -> str`,
  with timeouts, and they raise a typed error the callers turn into template fallbacks.
- Frontend: React 18 + Vite + TypeScript (strict) + Tailwind, Recharts, React Flow
  (`@xyflow/react`), Framer Motion, TanStack Query. API types generated from FastAPI's
  OpenAPI schema with `openapi-typescript`. Never hand-write API types.
- Tests: pytest, hypothesis. Frontend checks: `tsc --noEmit` and `vite build`.

## §4 Repository layout
```
prism-engine/
  CLAUDE.md  .env.example  .gitignore  README.md
  dev.sh  dev.ps1                     # start backend + frontend (macOS/Linux, Windows)
  docs/  PROGRESS.md  DECISIONS.md  BENCHMARK.md  DEMO_SCRIPT.md
  backend/
    requirements.txt  pyproject.toml (pytest config)
    app/
      main.py
      api/routes.py
      models/schemas.py               # all Pydantic models
      engine/
        config.py                     # ALL weights and constants
        loader.py                     # loads + caches data/*.json
        normalize.py  system1.py  solver.py  matcher.py  conflict.py
        market.py  scoring.py  skills.py  swot.py  roi.py  alternatives.py
        whatif.py  pipeline.py
      rag/ llm.py  index.py  explain.py  templates.py  chat.py
      data/
        careers/ technology.json engineering.json science.json health.json
                 arts_design.json finance_math.json hyperlocal.json
        exams.json  scholarships.json  cities.json
        questions_school.json  questions_college.json  demo_profiles.json
    scripts/ validate_data.py  warmup.py  benchmark.py  export_openapi.py
    tests/ test_*.py  benchmark_scenarios.json  calibration_set.json
  frontend/
    src/api/ client.ts  schema.d.ts (generated)
    src/pages/ Landing  StudentAssessment  ParentForm  Dashboard  PipelineInspector
    src/components/ (see §15)
    src/theme/ tokens.ts
```

## §5 Data model
### careers (one file per domain, 55–60 total)
Domains and minimum counts: Technology 10, Engineering 8, Science 6, Health 6,
Arts & Design 8, Finance & Maths 6, Hyper-local (agri-tech, manufacturing tech,
renewable energy tech, food processing, local entrepreneurship) 6.
```json
{
  "id": "ai_ml_engineer",
  "name": "AI/ML Engineer",
  "domain": "Technology",
  "steam": ["T", "M"],
  "summary": "Builds systems that learn from data.",
  "requirement_vector": {"numerical":0.85,"logical":0.9,"verbal":0.5,"spatial":0.4,
    "creative":0.5,"R":0.3,"I":0.95,"A":0.3,"S":0.2,"E":0.3,"C":0.5},
  "skills": [{"name":"Python","importance":0.9,"level_required":0.8}],
  "pathways": [{
    "id":"btech_govt",
    "label":"B.Tech CSE at a government/aided college",
    "entry":"after_class_12",
    "steps":["Class 12 PCM","JEE Main / KCET","B.Tech CSE","ML projects","Internship","Junior ML Engineer"],
    "duration_years":4,
    "cost_inr":{"min":200000,"max":500000},
    "institution_type":"govt",
    "entrance_exams":["jee_main","kcet"],
    "quality":0.8
  }],
  "salary_inr_lpa":{"entry":[6,12],"mid":[15,30],"senior":[30,60]},
  "growth_index":0.85, "job_velocity":0.8, "disruption_index":0.25,
  "stability":0.6, "risk_level":0.5, "prestige":0.7, "higher_studies_typical":false,
  "city_demand":{"bengaluru":0.95,"hyderabad":0.85,"chennai":0.7,"pune":0.75,
                 "mysuru":0.35,"delhi_ncr":0.8,"mumbai":0.75,"coimbatore":0.4},
  "adjacent_careers":["data_scientist","software_engineer","data_engineer"],
  "sources":["NIRF 2025 institutional fee disclosures","NCS portal occupation profile"],
  "data_note":"Indicative ranges for demonstration; verify before real-world use."
}
```
Rules: every career has 2–4 pathways mixing govt / private / online-or-diploma / lateral.
`entry` ∈ `after_class_10 | after_class_12 | graduate`. Every career has at least one
`after_class_12` pathway, and college-relevant careers have at least one `graduate`
(lateral) pathway. All 0–1 fields are floats in [0,1]. All 8 cities present in
`city_demand`. Skills use names from a shared vocabulary of about 60 skills.

### exams.json
`{id, name, level: "school"|"ug"|"pg", domains[], typical_month, source}`

### scholarships.json (25–35 entries)
`{id, name, provider, income_max_inr, levels[], domains[], amount_inr_per_year, source}`.
Use real, publicly known schemes and portals (e.g. National Scholarship Portal schemes,
state schemes, institutional merit schemes) described accurately. Do not invent scheme names.

### cities.json
`{id, name, state, top_sectors[]}` for bengaluru, mysuru, chennai, hyderabad, pune,
delhi_ncr, mumbai, coimbatore.

### questions_school.json / questions_college.json
- aptitude: 12 multiple-choice items (3 each: numerical, logical, verbal, spatial) with
  `answer` index. Class 9–12 difficulty for school, harder for college.
- riasec: 18 Likert items (3 per R, I, A, S, E, C).
- workstyle: 4 Likert items (creative, stability_vs_excitement, teamwork, structure).
- free_text: 2 prompts (see §6).
- college only: skills self-rating list (the 20 most common skills in the dataset).

### demo_profiles.json
Three complete profiles (student + parent answers) for the personas in §14.

## §6 Inputs
**Student, school track:** aptitude answers, RIASEC answers, workstyle answers, marks %,
favourite subjects, current class (9–12), stream if Class 11–12, home city, preferred
cities, willing_to_relocate, wants_higher_studies, risk_tolerance (low/medium/high),
dream_career_id (optional), free_text_1 "Something you made or did that you loved",
free_text_2 "What do you want your work to look like in 10 years?".
**Student, college track:** same psychometrics + degree, year, self-rated skills 0–100.
**Parent:** annual_income_inr, education_budget_inr (total), loan_willingness
(none/moderate/high), risk_appetite (low/medium/high), preferred_domains[],
location_preference (near_home/anywhere_india/abroad_ok), supports_higher_studies,
top_priority (stability/salary/prestige/happiness), free_text "Your hopes and concerns".
Profile completeness = answered fields / total fields (free text counts if ≥ 15 words).

## §7 Pipeline (pipeline.py → `PipelineResult` containing a full `PipelineTrace`)
### §7.1 Stage 1: Ingest Multi-Stakeholder Inputs
Validate with Pydantic. Record completeness.

### §7.2 Stage 2: Vectorize & Normalize
aptitude_dim = correct/3; Likert (x−1)/4 averaged per dimension; marks/100;
low/medium/high → 0.2/0.5/0.8. Student vector S (11 dims:
numerical, logical, verbal, spatial, creative, R, I, A, S, E, C) with creative =
mean(workstyle creative item, A-score). All values in [0,1].

### §7.3 Stage 3: System 1 Decision Layer (system1.py)
```python
class TypedDecision(BaseModel):
    question_id: str
    choice: str | None            # None when abstained
    probabilities: dict[str, float]
    confidence: float             # top probability
    margin: float                 # top1 - top2
    abstained: bool
    backend: str

class DecisionModel(Protocol):
    def decide(self, state: str, question_id: str, options: list[str],
               hypothesis_template: str) -> TypedDecision: ...
```
Backends: `ZeroShotNLIBackend` (default), `KeywordBackend` (offline fallback, confidence
capped at 0.5), `JevBackend` (stub raising `NotConfigured`; documents the upgrade path to
a commercial System One model).
Decisions:
- `student_domain_affinity`: free_text_1 + free_text_2 → the 7 domains (multi-label).
- `parent_concerns`: parent free_text → [financial burden, job security, distance from
  home, social prestige, child's happiness, uncertainty about new fields] (multi-label).
Abstain rule: confidence < 0.45 or margin < 0.15. Abstentions lower confidence (§7.8).
Optional: temperature scaling on `calibration_set.json` (~60 labelled texts) with ECE
reported in benchmark.py. Only use the word "calibrated" in UI or deck if this is done.

### §7.4 Stage 4: Financial Constraint Solver (solver.py)
- loan_factor: none 0, moderate 0.5, high 1.0. capacity = budget × (1 + loan_factor).
- cost_mid(p) = mean(cost_inr.min, cost_inr.max).
- expected_scholarship(p) = max over eligible scholarships of amount × duration_years,
  eligible when income ≤ income_max, level matches, domain matches. Cap at 60% of cost_mid.
- effective_cost(p) = cost_mid − expected_scholarship.
- Only pathways whose `entry` fits the student's current stage are candidates.
- Per career, choose the pathway with `scipy.optimize.milp`: binary x_p, maximize
  Σ x_p·(quality_p − λ·effective_cost_p/capacity), subject to Σ x_p = 1 and
  effective_cost_p·x_p ≤ capacity for each p (λ = 0.6). If infeasible, the career's
  status is `needs_aid` and the cheapest pathway is reported with its funding gap.
- Financial Fit (FF): 1.0 if cost ≤ budget; if budget < cost ≤ capacity,
  FF = 1 − 0.5·(cost − budget)/(capacity − budget); `needs_aid` → FF = 0.
  If capacity == budget, any cost > budget is `needs_aid` (no division).
- Output per career: status, chosen pathway, every pathway's evaluation (cost,
  scholarship, effective cost, feasible, objective value), funding gap.

### §7.5 Stage 5: Career Matcher (matcher.py)
Centred cosine: cos(S − 0.5, R − 0.5) mapped to [0,1] via (cos + 1)/2. Centring is required:
raw cosine of non-negative vectors bunches near 1 and doesn't discriminate.
Student Fit (SF) = 0.6·centred_cos + 0.25·domain_affinity[career.domain] +
0.15·academic_alignment, where academic_alignment = marks/100 weighted by how
numerical/verbal the career is.

### §7.6 Stage 6: Parent-Student Conflict Index + compromise (conflict.py)
Global index, dimensions with weights (sum 1):
- domain 0.25: 1 − Jaccard(student top-3 affinity domains, parent preferred_domains)
- risk 0.15: |student risk_tolerance − parent risk_appetite|
- location 0.15: student relocation (0/1) vs parent location_preference (0 / 0.5 / 1)
- higher_studies 0.15: |wants_higher_studies − supports_higher_studies|
- cost 0.15: clip((effective_cost of student's top career − budget)/budget, 0, 1)
- stability_vs_passion 0.15: student stability_vs_excitement item vs parent priority
  (stability 1.0, salary 0.7, prestige 0.6, happiness 0.2)
CI = 100·Σ w·mismatch. Return the per-dimension breakdown and the top 2 hotspots.
Per-career Parent Alignment (PA) = weighted mean of: domain match (1.0 if in
preferred_domains else 0.3), 1 − |risk_level − parent risk_appetite|, location fit
(city_demand[home city] if near_home, else 1.0), priority fit (stability → stability,
salary → normalized entry salary, prestige → prestige, happiness → SF), FF.
Each parent concern from System 1 with probability > 0.5 adds +0.1 weight to its
matching dimension; renormalize.
**Middle path (Nash bargaining):** U_s = SF, U_p = PA. Disagreement point
d = (median U_s, median U_p) over non-`needs_aid` careers. Middle path =
argmax (U_s − d_s)(U_p − d_p) over careers with both terms > 0. Return it plus each side's
gain vs that side's own top choice. If no career qualifies, return the career with the
highest min(U_s, U_p).

### §7.7 Stage 7: Market Intelligence (market.py)
Industry Hiring Index (MD) = 0.5·local_demand + 0.3·job_velocity + 0.2·(1 − disruption_index).
local_demand = city_demand[home city] if not willing_to_relocate, else max over preferred
cities (or all cities if none chosen). Report `best_city`.

### §7.8 Stage 8: Composite score, confidence, risk (scoring.py)
Growth (G) = 0.5·growth_index + 0.3·trajectory + 0.2·mobility_uplift, where
trajectory = clip((senior_mid/entry_mid − 1)/5, 0, 1) and
mobility_uplift = clip(log2(entry_mid_inr / annual_income_inr)/3, 0, 1)
(entry_mid_inr = mean(entry LPA) × 100000).
**PRISM Score = 30·SF + 20·FF + 20·MD + 15·G + 15·PA** (0–100, one decimal place).
Return points per component (e.g. Student Fit 26.4/30).
Confidence = 100·(0.4·completeness + 0.35·mean System 1 confidence over non-abstained
decisions, 0.3 if all abstained + 0.25·career data completeness).
Bands: High ≥ 75, Medium 55–74, Low < 55. Return `missing_inputs` that would raise it.
Risk Radar (0–1, higher = riskier): financial 1 − FF, skill_gap (§8 mean gap),
market 1 − MD, location (1 if home-city demand < 0.4 and not relocating, else
1 − local_demand), education_cost clip(effective_cost/annual_income/4, 0, 1),
disruption = disruption_index.

### §7.9 Stage 9: Ranking and outputs
Top careers = status ≠ needs_aid sorted by score (top 10). Stretch options = `needs_aid`
careers with SF in the top quartile, with aid options. Alternatives (§10). Middle path (§7.6).

## §8 Skill gap, roadmap, timeline (skills.py)
current skill level: college = self-rating/100; school = derived (numerical/logical/
verbal/spatial aptitude mapped to related skills, else 0.2 baseline).
gap = importance × max(0, level_required − current). Top gaps sorted descending.
Roadmap = chosen pathway steps interleaved with gap-ordered learning steps.
Timeline = roadmap steps placed on calendar years starting from the current year,
using the student's class/year and pathway duration.

## §9 SWOT (swot.py)
S: top 3 student dimensions with values. W: top 3 skill gaps for the #1 career.
O: top 3 high-demand opportunities in reachable cities + eligible scholarships + next exams.
T: disruption index of the top career, funding gap if any, top conflict hotspot.
Deterministic, structured output. System 2 may rephrase but never adds items.

## §10 ROI and alternatives (roi.py, alternatives.py)
break_even_years = effective_cost / (0.25 × entry_mid_inr). Show the 25% assumption
in the UI. Alternatives: if dream_career_id is set and is `needs_aid` or ranks outside
top 5, rank its adjacent_careers by score as "Closest realistic routes to your dream".

## §11 What-If (whatif.py)
Input: base assessment id (or full profile) + overrides: budget, loan_willingness,
home_city, willing_to_relocate, risk_tolerance, risk_appetite, wants_higher_studies,
top_priority. Re-run stages 2 and 4–9 reusing cached System 1 decisions. Target < 300 ms.
Output: new ranking, per-career rank delta and per-component point deltas, and one
reason sentence per career that moved ≥ 2 ranks or ≥ 3 points. The reason is built from
the largest component delta, e.g.
"AI/ML Engineer dropped from 91.0 to 82.4, mainly because Financial Fit fell from
17.0 to 9.0: the best-quality pathway now exceeds the budget."
No LLM in this path.

## §12 System 2 explanations (rag/)
- index.py: one Chroma document per career, pathway, scholarship and exam; metadata
  `{kind, id, career_id}`. Rebuilt by `python -m app.rag.index`.
- explain.py: for the top 5 careers + middle path, retrieve with
  `where={"career_id": {"$in": ids}}`. Prompt: answer only from CONTEXT and ENGINE_RESULT;
  return JSON `{career_id, why[3], why_not[2], roadmap_narrative, cited_ids[]}`;
  temperature 0.2. Calls go through `rag/llm.py` (§3).
- Numeric guardrail: extract every number and ₹ amount from the LLM output. Each must
  appear in ENGINE_RESULT or CONTEXT (normalize 5,00,000 / 500000 / 5 lakh / 5L).
  Replace any sentence failing the check with its template sentence. Log hits in the trace.
- templates.py: deterministic why / why-not / narrative from engine values, used when
  `LLM_PROVIDER=none`, the call fails, or JSON parsing fails.
- Fallbacks: System 1 model fails to load → KeywordBackend. LLM unavailable → templates.
  `DEMO_MODE=1` caches full results for demo profiles on disk.
  `scripts/warmup.py` pre-downloads all models.

## §13 API
- `GET  /api/health` → backends active (system1, llm provider + model), dataset counts, demo_mode
- `GET  /api/questions/{track}` → school | college question set
- `GET  /api/demo-profiles`
- `POST /api/assess` → `AssessmentResult` (id, ranking, details per career, conflict,
  middle_path, stretch_options, alternatives, swot, confidence, explanations, trace)
- `POST /api/whatif` → `WhatIfResult`
- `GET  /api/careers`, `GET /api/careers/{id}`
- `POST /api/chat` → `ChatReply` (§17)
- `GET  /api/chat/{assessment_id}` → saved chat history
Explanations may load lazily: `/api/assess` returns template text immediately, and
`GET /api/explanations/{assessment_id}` returns LLM text when ready.

## §14 Demo personas
1. **Ananya**: Class 12 PCM, Mysuru, strong numerical/logical, high I, free text about
   building a chatbot. Family income ₹7,00,000, budget ₹5,00,000, moderate loan, medium
   risk, prefers Technology/Engineering, near_home, priority stability.
   Expected story: AI/ML Engineer near the top; conflict hotspots on location and risk;
   middle path is a software/AI route via a govt college near home; What-If budget
   ₹5L → ₹3L visibly re-ranks with a Financial Fit reason.
2. **Rahul**: 2nd-year B.Com, college track, Chennai, interested in data analytics,
   income ₹4,00,000, budget ₹1,50,000, no loan, low risk, prefers Finance & Maths.
   Expected: data/finance-analytics careers via lateral and online pathways; strong
   skill-gap roadmap; eligible scholarships shown.
3. **Meera**: Class 10, Bengaluru, high spatial/creative/A, income ₹18,00,000, budget
   ₹10,00,000, high loan, parents prefer Health, priority prestige.
   Expected: Arts & Design careers (architecture, UX design) top for the student;
   high conflict index on domain; Nash middle path shown (e.g. a design-plus-health or
   architecture route) with gains for both sides.
After Phase 4, tune only the persona answers (never formulas) so each story holds, and
record any tuning in DECISIONS.md.

## §15 Frontend design
Concept: a prism splits one light into a spectrum. PRISM splits one decision into five
visible components, each with a fixed colour used everywhere.
Tokens: ink #1B1F3B, paper #F7F8FB, surface #FFFFFF, line #E3E6EF,
Student Fit #6C4CF1, Financial Fit #0E9F8E, Market Demand #D9930D, Growth #2F7DE1,
Parent Alignment #D63F74. Dark-mode not required.
Type: "Bricolage Grotesque" (headings, 600) and "IBM Plex Sans" (body, 400/500) from
Google Fonts. Type scale 14 / 16 / 20 / 28 / 40.
Rules: sentence case; no all-caps labels; no numbered markers unless the content is a
true sequence; plain language from the student's or parent's point of view; one motion
moment only (What-If re-rank), reduced-motion respected; visible keyboard focus;
works at 375 px and 1440 px.
Signature component: **PrismBar**, a career's score as one horizontal bar split into five
coloured segments sized by points earned, with a tooltip per segment.
Components: PrismBar, ScoreBreakdown, ConfidenceBadge, ConflictPanel, MiddlePathCard,
RiskRadar, SkillGap, PathwayGraph, Timeline, CityDemand, SwotGrid, RoiCard,
AidOptions, StretchOptions, WhatIfDrawer, StageCard (inspector), ChatPanel (§17).
Dashboard order: top careers → selected career detail (breakdown, why/why-not,
confidence) → family alignment (conflict + middle path) → risk radar + skill gap →
pathway graph + timeline → city demand + SWOT → ROI + scholarships/exams → stretch options.
PipelineInspector: the stages as a vertical sequence; each StageCard expands to show its
real trace values (vectors, System 1 probabilities and abstentions, solver pathway table,
conflict breakdown, score components, guardrail hits).

## §16 Testing and honest metrics
- Unit tests per engine module.
- `benchmark_scenarios.json`: 30 profiles with expected constraints (e.g. "no career
  marked feasible exceeds capacity", "ai_ml_engineer in top 5 for Ananya").
- Property tests (hypothesis, max_examples=1000): feasible ⇒ effective_cost ≤ capacity;
  lowering budget never increases any FF; CI ∈ [0,100]; scores ∈ [0,100]; component
  points sum to the score (±0.1); What-If with no overrides gives zero deltas;
  the pipeline is deterministic for identical input.
- `scripts/benchmark.py` writes docs/BENCHMARK.md with exact counts. The deck quotes
  only these numbers.
- Chat tests (LLM mocked): intent routing, a What-If asked in chat matches /api/whatif
  exactly, numeric guardrail, `none`-mode answers, history saved and reloaded.

## §17 "Ask PRISM" chatbot
Purpose: the student or parent asks questions about THEIR results in plain words.
It is grounded in everything they entered and everything the engine computed.

**UI (ChatPanel):** an "Ask PRISM" button on the dashboard opens a side panel (desktop) or
a bottom sheet (mobile). A switch "Asking as: student / parent" changes tone only.
Show 5 suggested questions built from the result, e.g. "Why is <#1 career> ranked first?",
"What if our budget is ₹3,00,000?", "Which scholarships can I apply for?",
"What should I learn first?", "Why not <dream career>?". Each reply shows small source
chips (career, scholarship or exam ids) and, for what-if answers, a "Show on dashboard"
button that opens the WhatIfDrawer with the same values. A one-line note under the input:
"Answers use your results. Money values are indicative estimates." When the provider is
external, add: "Your answers are sent to <provider> to write replies."
No streaming; show a typing indicator. The panel opens without animation (the What-If
re-rank stays the only motion moment). Chat history is stored in SQLite per assessment,
never in browser storage.

**Backend (`rag/chat.py`), per message:**
1. Build CONTEXT (compact JSON, ≤ 6,000 tokens): student and parent inputs (no free-text
   longer than 300 characters each), top 10 ranking with component points, details for the
   selected and mentioned careers (pathway, cost, scholarship, skill gaps, roadmap,
   timeline, ROI, risk radar, city demand), conflict breakdown and middle path, SWOT,
   stretch options, alternatives, eligible scholarships and exams, plus Chroma retrieval
   for the question (filtered to careers in the result or named in the question), plus
   the last 8 chat turns.
2. Route the question with `complete_json` into
   `{intent: explain|compare|whatif|scholarships|plan|other, career_ids[], overrides{}}`
   (overrides use the §11 fields; parse amounts like "3 lakh", "₹3,00,000", "3L").
   Validate with Pydantic. If the LLM fails or returns invalid JSON, use a rule-based
   router (keywords, career names, city names, regex for amounts).
3. If intent is `whatif`, run engine/whatif.py with the overrides and add its result
   (new ranks, point deltas, reason sentences) to CONTEXT. If `compare`, add both careers'
   component points. The LLM never computes numbers.
4. Answer with `complete_text`: answer only from CONTEXT; at most 120 words; plain language
   for a Class 9–12 student or a parent; say clearly when something isn't in the results and
   which input would help; never promise admission, salary or outcomes; politely steer
   off-topic questions back to career planning.
5. Run the §12 numeric guardrail on the answer. Remove sentences with unsupported numbers;
   if nothing useful is left, use the template answer for that intent.
6. Return `ChatReply {answer, intent, sources[], whatif?, guardrail_hits, provider}`.
**Fallback (`none` or any failure):** rule-based router + template answers for every intent
built from engine values, so the chat works offline on stage.
**Care rule:** if a message shows serious distress (for example family pressure that feels
unbearable, or thoughts of self-harm), reply kindly, encourage talking to a trusted adult or
school counsellor, and show Tele-MANAS 14416 (India's free mental-health helpline). Do not
continue career advice in that reply.
