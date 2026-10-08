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

## Phase 2B: Engine part 2 (2026-10-08)

**Built**
- `engine/conflict.py` (§7.6): Conflict Index with breakdown and top 2 hotspots, per-career Parent
  Alignment, concern weighting, Nash middle path with max-min fallback.
- `engine/market.py` (§7.7), `engine/scoring.py` (§7.8–§7.9: Growth, PRISM score with exact component
  points, per-career confidence with missing inputs, risk radar, top-10 ranking).
- `engine/skills.py` (§8), `engine/swot.py` (§9), `engine/roi.py` (§10), `engine/alternatives.py`
  (§10 dream alternatives, §7.9 stretch options with aid).
- `TypedDecision` and result models in `schemas.py`; constants in `config.py`.

**Checks**
- `pytest -q`: 112 passed (new: conflict incl. identical → 0 and fully opposed → 94, market, scoring,
  skills, SWOT, ROI, alternatives).
- `python scripts/validate_data.py`: 0 errors. `npm run typecheck`, `npm run build`: passed.
- Meera end-to-end with a stand-in domain affinity: CI 39.2 (hotspots domain, location); Nash middle
  path = Architect, Biomedical Engineer second, matching §14.

**Known issues**
- The Meera example uses a hand-set domain affinity until System 1 exists (Phase 3).

## Phase 2C: Proof (2026-10-08)

**Built**
- `tests/test_properties.py`: all 7 §16 properties with hypothesis (1,000 examples each, seed 20261008),
  on random valid profiles built from the input models and the real question sets (`tests/strategies.py`).
- `tests/engine_chain.py`: runs engine stages 2 and 4–9 in order (stand-in until pipeline.py / whatif.py exist).
- `tests/benchmark_scenarios.json`: 30 constraint-only scenarios plus 3 tracked §14 persona checks.
- `scripts/benchmark.py`: runs scenarios and properties, writes `docs/BENCHMARK.md` with counted results.

**Bugs found by the properties and fixed**
- Lowering the budget could raise Financial Fit, because the solver switched to a cheaper pathway. FF now uses
  the cheapest stage-fit pathway (user decision). New hand test in `test_solver.py`.
- Speed: all careers are now solved in one MILP. One engine run went from about 50 ms to about 8 ms. A test
  checks that the combined solve matches solving each career alone.

**Checks**
- `pytest -q`: 121 passed (incl. 7 properties × 1,000 profiles; about 2 minutes).
- `python scripts/benchmark.py`: 30 / 30 scenarios (70 / 70 constraints), 7 / 7 properties, 7,000 random profiles.
- `python scripts/validate_data.py`: 0 errors. `npm run typecheck`, `npm run build`: passed.

**Known issues**
- Tracked §14 stories, to be handled in the post-Phase-4 persona tuning:
  - Ananya's second hotspot is domain, not risk.
  - Rahul's roadmap has 1 learning step: his strong numerical aptitude covers skills he did not rate.
  - Rahul's #1 pathway is an online certificate, so SWOT shows no scholarships for it.
- When one component changes, rounding can move 0.1 point between the others. Phase 5 What-If reasons should use component values.

## Phase 3: System 1 (2026-10-08)

**Built**
- `engine/system1.py`: `DecisionModel` protocol, `ZeroShotNLIBackend` (multi-label, lazy, loads once, float32),
  `KeywordBackend` (offline, confidence capped at 0.5), `JevBackend` stub raising `NotConfigured`,
  §7.3 abstain rule, `run_decisions()` for `student_domain_affinity` and `parent_concerns`.
- Factory with automatic fallback: SYSTEM1_MODEL → light fallback model → KeywordBackend. New `SYSTEM1_BACKEND` setting.
- System 1 loads at server startup; `/api/health` reports the active backend.
- `scripts/warmup.py`: downloads and loads all three models, then shows persona decisions with timings.
- Tests: `test_system1.py` (keyword backend, abstain rule, factory fallbacks), `test_system1_model.py` (slow, real model).

**Checks**
- `python scripts/warmup.py`: 3 / 3 models loaded (DeBERTa 8.5 s, DistilBERT 1.0 s, MiniLM 4.4 s).
- `pytest -q`: 140 passed. `pytest -q -m slow`: 1 passed.
- `python scripts/validate_data.py`: 0 errors. `python scripts/benchmark.py`: 30 / 30 scenarios, 7 / 7 properties.
- `npm run typecheck`, `npm run build`: passed. Live `/api/health`: `zero_shot_nli:MoritzLaurer/deberta-v3-base-zeroshot-v2.0`.

**Persona decisions (real model, about 0.5–0.9 s each)**
- Ananya: domain Technology (1.00, margin 0.96); concerns abstained (job security, new fields, distance, money all ≥ 0.97).
- Rahul: domain abstained (Finance & Maths 1.00, Technology 0.99); concerns abstained (job security 1.00, money 0.99).
- Meera: domain Arts & Design (0.99); concerns job security (0.91).

**Known issues**
- Multi-label + the §7.3 margin rule: when several labels clearly apply, the decision abstains. 3 of the 6 persona
  decisions abstain, which lowers their §7.8 confidence. The probabilities still drive domain affinity and parent
  concern weights. Changing this would change a §7.3 formula, so it is left as specified.
- Optional §7.3 temperature scaling on calibration_set.json is not done; the word "calibrated" must not be used.

## Phase 4: Pipeline, What-If and API (2026-10-08)

**Built**
- `engine/pipeline.py`: runs stages 1–9 and returns a `PipelineResult` with a `PipelineTrace` of every value
  (completeness, vectors, System 1 decisions, solver pathway table, fits, conflict + Parent Alignment, market, growth,
  scores, confidence, risk, ranking order). Career details for the top 10, middle path, stretch options, dream alternatives.
- `engine/whatif.py`: re-runs stages 2 and 4–9 with saved System 1 decisions; rank and per-component deltas for every
  career; §11 reason sentences. `engine/formatting.py` (₹ Indian grouping).
- `rag/templates.py`: deterministic why / why-not / roadmap narrative for the top 5 + middle path.
- `app/storage.py` (SQLite via SQLAlchemy), `app/demo_cache.py` (DEMO_MODE disk cache), `app/services.py`.
- All §13 endpoints: health (now with dataset counts), questions (answer keys hidden), demo-profiles, assess, whatif,
  explanations, careers, careers/{id}.
- Property tests and benchmark moved onto the real pipeline; new full-pipeline persona scenarios with the real System 1.
- Persona tuning: Rahul (2 answers). Vite proxy now targets 127.0.0.1.

**Checks**
- `pytest -q`: 184 passed (new: test_api 18, test_pipeline 7, test_whatif 8, test_templates 11). `pytest -q -m slow`: 1 passed.
- `python scripts/benchmark.py`: 30 / 30 engine scenarios (70 / 70), 5 / 5 full-pipeline persona scenarios (22 / 22),
  7 / 7 properties, 7,000 random profiles. What-If median 34 ms, slowest 47 ms over 20 runs.
- `python scripts/export_openapi.py`: written. `npm run gen:api`, `npm run typecheck`, `npm run build`: passed.
- `python scripts/validate_data.py`: 0 errors.
- Live server with the real model: assess about 1.4 s (System 1 about 1 s), What-If about 40 ms per request.

**Known issues**
- Ananya's second hotspot is domain, not risk (user chose to keep §14's answers; tracked in the benchmark).
- Ananya's ₹3L What-If changes the top 10 but not the top 5 order much; AI/ML Engineer keeps FF 1.0 through its online pathway.
- Rahul's #1 (Data Analyst 82.6) is only 0.1 ahead of Financial Analyst (82.5).
- Ananya's middle path is her own #1 (AI/ML Engineer via a govt B.Tech): she gives up nothing, and the parents gain
  +0.121 over the median.

## Phase F1: Assessment screens + main dashboard (2026-10-08)

**Built**
- Foundation: react-router, typed API client + TanStack Query hooks (`src/api/client.ts`, `queries.ts`, types only from
  the generated schema), layout shell with engine status, primitives Button, Card, Field, Choice (radio/checkbox), MoneyInput,
  Stepper, Badge; spacing/radius tokens in `tokens.ts`.
- Landing: one-line pitch, "I'm in school" / "I'm in college", three "Try a demo family" cards that run POST /api/assess.
- StudentAssessment: About you, Aptitude, Interests, Work style, In your words, Preferences (+ Skills for college), loaded
  from /api/questions/{track}; per-step validation, inline errors, error summary that takes focus, progress bar, back/next.
- ParentForm: "Hand the device to your parent" screen, money inputs with Indian grouping (5,00,000) and amount in words.
- Dashboard: PrismBar (tooltip per segment on hover, tap and keyboard), top-careers list, selected career with
  ScoreBreakdown, ConfidenceBadge with missing-input hints, why / why-not, ConflictPanel, MiddlePathCard, StretchOptions
  with AidOptions; loading and error states.

**Checks**
- `npm run typecheck`, `npm run build`: passed after each part.
- `pytest -q`: 184 passed.
- Live servers (real DeBERTa System 1): Ananya, Rahul, Meera through the Vite proxy, 1.2–1.4 s each; every section
  has content (10 top careers, breakdown, confidence, why/why-not, 6 conflict dimensions, middle path, stretch options).
- Headless Edge: all three dashboards at 1440 px and 375 px, no horizontal page scroll, no console errors; PrismBar
  tooltip shows on mouse hover and on Tab with a visible focus outline; full college + parent form filled and submitted
  to a dashboard.

**Known issues**
- Reloading a dashboard page clears it (no GET endpoint for saved assessments; see DECISIONS.md).
- Ananya and Meera have no stretch options (all good-fit careers are affordable); the section says so in a sentence.
- Ananya's confidence badge shows 100.0 with a hint about parent free text: the hint comes from the abstained
  parent_concerns decision (§7.8 missing_inputs).
- The selected career's suggested route appears both above the breakdown and inside the template narrative.
