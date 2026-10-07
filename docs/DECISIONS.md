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
