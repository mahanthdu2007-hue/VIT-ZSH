# Decisions

date | decision | reason
--- | --- | ---
2026-10-08 | Renamed `CLAUDE .md` to `CLAUDE.md` | Matches the §4 layout and lets Claude Code load it automatically.
2026-10-08 | Backend venv uses Python 3.11 (machine default is 3.14) | §3 specifies Python 3.11; CPU PyTorch and transformers support it fully.
2026-10-08 | Parent Alignment uses equal weights (0.2 each) for domain, risk, location, priority, FF | §7.6 says "weighted mean" but gives no weights; equal weights are the simplest neutral choice.
2026-10-08 | Parent concern → PA dimension map: financial burden→FF, job security→risk, distance from home→location, social prestige→priority, child's happiness→priority, uncertainty about new fields→domain | §7.6 says each concern boosts "its matching dimension" without listing the matches; this is the most direct reading.
2026-10-08 | Settings live in `app/settings.py` | §4 has no settings file; a small separate module keeps main.py focused.
2026-10-08 | Test client uses `httpx2` instead of `httpx` | Starlette deprecated `httpx` for its TestClient and warns on every test run.
2026-10-08 | TypeScript pinned to 5.x | TypeScript 7 has no JavaScript compiler API, which `openapi-typescript` needs for `npm run gen:api`.
2026-10-08 | Tailwind 3 with theme built from `src/theme/tokens.ts` | Lets `tailwind.config.ts` import tokens directly, so colours and type exist in one place (§15).
2026-10-08 | Phase 0 page is `src/pages/HealthPage.tsx` | The five §4 pages belong to later phases; this is a temporary status page.
2026-10-08 | Scholarships gain `restricted_to` (null = open to all) and nullable `income_max_inr` (null = no income limit) | Asked the user: most real schemes are limited by caste category, gender, state or institution, which the §5 format could not record. Engine cost maths will count only unrestricted schemes; restricted ones are shown as "you may qualify".
2026-10-08 | Scholarship and pathway study levels use `school / diploma / ug / pg` | §5 does not list level values; these match exam levels plus diploma.
2026-10-08 | `institution_type` ∈ `govt / private / online / diploma`; a lateral pathway is one with `entry = graduate` | §5 says "govt / private / online-or-diploma / lateral"; lateral describes entry, not institution.
2026-10-08 | Added `data/skills_vocabulary.json` with `{name, category, aptitude}`; `aptitude` links a skill to numerical/logical/verbal/spatial | Phase 1A asks for the file; §8 needs the aptitude-to-skill mapping for school students.
2026-10-08 | College skills list is a hand-picked 20 for now; the validator warns if it differs from the 20 most common career skills | §5 says "the 20 most common skills in the dataset", but there are no careers yet.
2026-10-08 | Missing `graduate` pathway is a validator warning, not an error | §5 requires it only for "college-relevant" careers, which is not defined.
2026-10-08 | Student fields marks, subjects, preferred cities, dream career and free text are optional; class/year, home city, relocation, higher studies and risk are required | §6 completeness counts answered fields, so some must be optional; the engine cannot run without the required ones.
2026-10-08 | `stability_vs_excitement` item is worded so agreeing means preferring stability | Lets §7.6 compare it directly with the parent's stability value.
2026-10-08 | Single-valued `typical_month` uses the first or main sitting for exams held several times a year (e.g. JEE Main → January) | §5 schema has one month per exam.
2026-10-08 | Validator: a domain with no careers yet is a warning; a domain with careers must meet its §5 minimum; the 55–60 total is enforced once every domain has careers | Careers are written in batches (Phase 1B onward); a batch must not fail on domains that belong to later batches, but written domains are still checked fully.
2026-10-08 | Added TANCET (Anna University, MCA/MBA) to exams.json | Needed for the MCA lateral pathway into software careers.
2026-10-08 | Pathway `cost_inr` is total tuition and fees for the whole pathway, excluding living costs | §5 gives one range per pathway; tuition is what fee disclosures publish.
2026-10-08 | Career `sources` name the source type per value group ("Costs: …", "Salaries: …", "Demand and growth: …", "Skills: …") | Phase 1B asks that sources name where each value would come from.
2026-10-08 | Requirement vectors tuned so the centred cosine between any two careers is ≤ 0.92 (mean 0.49) | Phase 1B: vectors must differ clearly; the §7.5 matcher uses centred cosine, so that is the measure checked.
