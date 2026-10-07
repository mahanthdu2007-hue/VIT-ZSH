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
