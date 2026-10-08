# Progress

## Phase 0: Setup and skeleton (2026-10-08)

**Built**
- Repository: git, `.gitignore`, `.env` / `.env.example` (LLM_PROVIDER=none, offline defaults), docs.
- Backend: Python 3.11 venv, CPU-only PyTorch 2.14.1, pinned `requirements.txt`; FastAPI app with
  CORS for http://localhost:5173, settings from `../.env`, `GET /api/health`
  (status, system1 = "not_loaded", llm provider, demo_mode); `app/engine/config.py` with every
  §6–§12 weight, threshold and constant; `scripts/export_openapi.py`; `tests/test_health.py`.
- Frontend: Vite 8 + React 18 + TypeScript 5 (strict) + Tailwind 3; `/api` proxied to :8000;
  `src/theme/tokens.ts` (§15) feeding the Tailwind theme; Google Fonts; generated
  `src/api/schema.d.ts`; a status page that fetches `/api/health` with TanStack Query.
- `dev.sh`, `dev.ps1`, `README.md`.

**Checks**
- `pytest -q`: 2 passed.
- `npm run typecheck`: passed.
- `npm run build`: passed.
- Live run via `dev.ps1`: both servers started; `/api/health` answered 200 directly and through the
  Vite proxy; headless Edge showed the status page with the health values.

**Known issues**
- `npm audit` reports 7 warnings (2 moderate, 5 high) in Tailwind 3's build-time tools
  (micromatch, postcss-selector-parser). They run only during development and never ship.
  The only fix is upgrading to Tailwind 4 (breaking change).
- `dev.sh` has not been run (no macOS/Linux machine here).

## Phase 1A: Data foundations (2026-10-08)

**Built**
- `app/models/schemas.py`: Career, Pathway, Skill, Exam, Scholarship, City, SkillVocabularyEntry,
  QuestionSet (with item models), school/college student inputs and parent input (§6), Dataset.
- `app/engine/loader.py`: loads and caches all data files through the models; errors name the file.
- Data: `cities.json` (8), `exams.json` (28 real exams, school/UG/PG, all 7 domains incl. design,
  architecture, medical), `scholarships.json` (32 real schemes, 7 open to everyone, rest marked with
  `restricted_to`), `skills_vocabulary.json` (60), `questions_school.json`, `questions_college.json`.
- `scripts/validate_data.py`: schema, ranges, uniqueness, cross-references, §5 counts, summary table.
- New §5/§6 constants in `config.py`.

**Checks**
- `python scripts/validate_data.py`: 0 errors, 1 warning (no careers yet, as expected).
- `pytest -q`: 9 passed (includes a test proving the validator fails on broken data).
- `npm run typecheck`, `npm run build`: passed.
- Aptitude answers re-computed independently in Python: all 24 correct and unique.

**Known issues**
- Scholarship amounts are indicative; several schemes pay different amounts by course, and the
  lower or typical figure is used.
- College skills list must be re-checked against the 20 most common career skills after careers are added.

## Phase 1B: Careers batch 1 (2026-10-08)

**Built**
- `data/careers/technology.json` (10), `engineering.json` (8), `science.json` (6): 24 careers, each with
  3–4 pathways mixing govt / private / diploma-or-online / graduate (lateral) entry.
- Added TANCET to `exams.json`.
- Validator now treats unwritten domains as warnings and enforces the total once all domains exist
  (new test covers this).

**Checks**
- `python scripts/validate_data.py`: 0 errors, 2 warnings (4 domains not written yet; college skills
  list to re-check after all careers exist). Ran after each file: 0 errors each time.
- `pytest -q`: 10 passed. `npm run typecheck`, `npm run build`: passed.
- Requirement vector distinctness: closest pair centred cosine 0.92, mean 0.49, smallest spread 0.40.

**Known issues**
- All costs and salaries are indicative.
- College skills list (questions_college.json) still to be matched to the 20 most common skills once
  every batch is written.

## Phase 1C: Careers batch 2 (2026-10-08)

**Built**
- `data/careers/health.json` (8), `arts_design.json` (8), `finance_math.json` (8), `hyperlocal.json` (7).
  Dataset now has 55 careers; every domain meets its §5 minimum.
- Arts & Design and Hyper-local careers each have at least one low-cost route (government art school,
  polytechnic diploma, government tool room, ITI, RSETI, online course).
- `questions_college.json` skills list now matches the 20 most common career skills.
- Added `nift_pg` exam and "Audio production and sound design" skill.

**Checks**
- `python scripts/validate_data.py`: 0 errors, 6 warnings (licensed professions with no lateral route,
  by design). Ran after each file: 0 errors each time.
- `pytest -q`: 10 passed. `npm run typecheck`, `npm run build`: passed.
- Requirement vectors across all 55 careers: max centred cosine 0.92, mean 0.20, smallest spread 0.35.

**Known issues**
- All costs and salaries are indicative.

## Phase 1D: Demo profiles and data audit (2026-10-08)

**Built**
- `DemoProfile` model, loaded with the dataset; `data/demo_profiles.json` with Ananya, Rahul and Meera,
  every field filled. Hand-computed §7.2 vectors match §14: Ananya numerical/logical/I = 1.0;
  Rahul numerical 1.0, C 0.92; Meera spatial/A/creative = 1.0. Free text 46–53 words each.
- Dataset audit: no duplicate ids or names, no cost min > max, all salaries rise entry → mid → senior,
  closest requirement-vector pair 0.92 centred cosine. Nothing needed fixing.
- Validator: new permanent checks for the audit items and for demo profiles (with tests).

**Checks**
- `python scripts/validate_data.py`: 0 errors, 6 warnings (licensed professions, by design).
- `pytest -q`: 12 passed. `npm run typecheck`, `npm run build`: passed.

**Known issues**
- Ananya's §14 story expects hotspots "location and risk". With parent preferences Technology +
  Engineering, the domain mismatch (≥ 1/3 × 0.25) can outrank risk (0.3 × 0.15) depending on System 1
  output. Check after Phase 4 and tune persona answers only, as §14 allows.

## Phase 2A: Engine part 1 (2026-10-08)

**Built**
- `engine/normalize.py` (§7.2): student vector, student and parent preference values, completeness
  with missing-field names.
- `engine/solver.py` (§7.4): capacity, cost_mid, scholarship eligibility (open schemes only) with 60% cap,
  effective cost, stage filtering, `scipy.optimize.milp` pathway choice with deterministic tie-break,
  Financial Fit (capacity == budget handled without division), needs_aid / no_pathway, funding gap,
  full per-pathway evaluation.
- `engine/matcher.py` (§7.5): centred cosine, academic alignment (blend), Student Fit.
- Result models in `schemas.py`; constants in `config.py`. Competitive scholarships marked restricted.

**Checks**
- `pytest -q`: 55 passed (normalize, solver, matcher: hand-calculated cases and edge cases for zero
  budget, no loan, all pathways unaffordable, 60% cap, stage filtering, exact ties).
- `python scripts/validate_data.py`: 0 errors. `npm run typecheck`, `npm run build`: passed.

**Known issues**
- None new.
