"""§16 benchmark: runs tests/benchmark_scenarios.json and the property tests, writes docs/BENCHMARK.md.

Usage (from backend/): python scripts/benchmark.py
"""

import json
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[1]
TESTS = BACKEND / "tests"
sys.path[:0] = [str(BACKEND), str(TESTS)]

from engine_chain import ChainResult, apply_overrides, deltas, run  # noqa: E402
from test_properties import MAX_EXAMPLES, PROPERTIES, SEED, hypothesis_test  # noqa: E402

from app.engine import config  # noqa: E402
from app.engine.loader import get_dataset  # noqa: E402
from app.engine.solver import capacity  # noqa: E402
from pydantic import TypeAdapter  # noqa: E402

from app.models.schemas import Dataset, ParentInput, StudentInput  # noqa: E402

SCENARIOS = TESTS / "benchmark_scenarios.json"
OUTPUT = BACKEND.parent / "docs" / "BENCHMARK.md"
POINTS_TOLERANCE = 0.1  # §16
STUDENT_ADAPTER: TypeAdapter[StudentInput] = TypeAdapter(StudentInput)


class Case:
    """One scenario's inputs, its engine result, and (if it has What-If overrides) the re-run."""

    def __init__(self, scenario: dict[str, Any], data: Dataset) -> None:
        self.data = data
        self.careers = {c.id: c for c in data.careers}
        self.student, self.parent = build_inputs(scenario["profile"], data)
        self.affinity = {d: 0.0 for d in config.DOMAINS} | scenario.get("domain_affinity", {})
        self.concerns = scenario.get("parent_concerns", {})
        self.result = run(self.student, self.parent, self.affinity, self.concerns, data)
        self.whatif: ChainResult | None = None
        if "whatif" in scenario:
            student, parent = apply_overrides(self.student, self.parent, scenario["whatif"])
            self.whatif = run(student, parent, self.affinity, self.concerns, data)

    def top(self, n: int) -> list[str]:
        return [s.career_id for s in self.result.ranking[:n]]


def build_inputs(profile: dict[str, Any], data: Dataset) -> tuple[StudentInput, ParentInput]:
    """A demo profile with the scenario's field overrides applied (validated again)."""
    demo = next(p for p in data.demo_profiles if p.id == profile["demo"])
    student = STUDENT_ADAPTER.validate_python(demo.student.model_dump() | profile.get("student", {}))
    parent = ParentInput.model_validate(demo.parent.model_dump() | profile.get("parent", {}))
    return student, parent


def _require_whatif(case: Case) -> ChainResult:
    if case.whatif is None:
        raise ValueError("this check needs a 'whatif' block in the scenario")
    return case.whatif


def no_feasible_exceeds_capacity(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    cap = capacity(case.parent)
    over = [f.career_id for f in case.result.finances.values()
            if f.status == "feasible" and (f.effective_cost or 0) > cap]
    return not over, f"capacity {cap:,}; over capacity: {over or 'none'}"


def career_in_top(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    top = case.top(c["n"])
    return c["career"] in top, f"top {c['n']}: {top}"


def domain_in_top(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    top = case.top(c["n"])
    found = [t for t in top if case.careers[t].domain in c["domains"]]
    return len(found) >= c.get("at_least", 1), f"{c['domains']} in top {c['n']}: {found}"


def top_career_domain_in(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    top = case.top(1)
    domain = case.careers[top[0]].domain if top else None
    return domain in c["domains"], f"#1 {top} is {domain}"


def top_chosen_entry_in(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    entries = []
    for career_id in case.top(c["n"]):
        finance = case.result.finances[career_id]
        entries.append(next(p.entry for p in finance.pathways if p.pathway_id == finance.chosen_pathway_id))
    return all(e in c["entries"] for e in entries), f"chosen entries of top {c['n']}: {sorted(set(entries))}"


def status_is(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    status = case.result.finances[c["career"]].status
    return status == c["status"], f"{c['career']} is {status}"


def feasible_count(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    count = sum(f.status == "feasible" for f in case.result.finances.values())
    return c.get("min", 0) <= count <= c.get("max", len(case.careers)), f"{count} feasible careers"


def all_feasible_ff_equal(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    values = {round(f.financial_fit, 9) for f in case.result.finances.values() if f.status == "feasible"}
    return values <= {c["value"]}, f"feasible FF values: {sorted(values)}"


def conflict_between(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    index = case.result.conflict.index
    return c.get("min", 0) <= index <= c.get("max", 100), f"CI {index:.1f}"


def hotspot_includes(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    hotspots = case.result.conflict.hotspots
    return c["dimension"] in hotspots, f"hotspots {hotspots}"


def middle_path_check(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    mp = case.result.middle_path
    if mp is None:
        return False, "no middle path"
    ok = case.result.finances[mp.career_id].status == "feasible"
    if "method" in c:
        ok = ok and mp.method == c["method"]
    if c.get("both_gain"):
        ok = ok and mp.student_gain > 0 and mp.parent_gain > 0
    if "domains" in c:
        ok = ok and case.careers[mp.career_id].domain in c["domains"]
    return ok, (f"{mp.career_id} ({case.careers[mp.career_id].domain}) via {mp.method}; "
                f"gains student {mp.student_gain:+.3f}, parent {mp.parent_gain:+.3f}")


def stretch_options_valid(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    options = case.result.stretch
    all_need_aid = all(case.result.finances[o.career_id].status == "needs_aid" for o in options)
    with_aid = all(o.cheaper_pathways for o in options)
    return (all_need_aid and with_aid and c.get("min", 0) <= len(options) <= c.get("max", len(case.careers)),
            f"{len(options)} stretch options: {[o.career_id for o in options][:5]}")


def dream_alternatives_check(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    dream = case.result.dream
    if c.get("reason") is None:
        return dream is None, f"dream alternatives: {dream.reason if dream else 'none'}"
    ok = dream is not None and dream.reason == c["reason"] and bool(dream.alternatives)
    return ok, f"dream alternatives: {dream.reason if dream else 'none'}, " \
               f"{[a.career_id for a in dream.alternatives] if dream else []}"


def scholarship_applied(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    used = sorted({e.scholarship_id for f in case.result.finances.values() for e in f.pathways
                   if e.scholarship > 0 and e.scholarship_id})
    return len(used) >= c["min"], f"{len(used)} schemes lower a pathway cost: {used[:5]}"


def scholarship_cap_respected(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    over = [(f.career_id, e.pathway_id) for f in case.result.finances.values() for e in f.pathways
            if e.scholarship > round(config.SCHOLARSHIP_CAP_FRACTION * e.cost_mid)]
    return not over, f"pathways above the 60% cap: {over or 'none'}"


def roadmap_learning_steps(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    plan = case.result.top_plan
    steps = sum(s.kind == "learning" for s in plan.roadmap) if plan else 0
    return steps >= c["min"], f"{steps} learning steps for {plan.career_id if plan else None}"


def swot_items(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    swot = case.result.top_swot
    items = [o for o in (swot.opportunities if swot else []) if o.kind == c["kind"]]
    return len(items) >= c["min"], f"{len(items)} {c['kind']} opportunities: {[o.label for o in items]}"


def scores_valid(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    scores = case.result.scores.values()
    in_range = all(0 <= s.score <= 100 for s in scores)
    sums = all(abs(sum(s.points.values()) - s.score) <= POINTS_TOLERANCE for s in scores)
    return in_range and sums, f"{len(scores)} scores in [0, 100] with matching points: {in_range and sums}"


def whatif_ff_not_higher(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    after = _require_whatif(case)
    raised = [k for k, f in after.finances.items() if f.financial_fit > case.result.finances[k].financial_fit + 1e-9]
    return not raised, f"careers whose FF rose: {raised or 'none'}"


def whatif_rank_changes(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    after = _require_whatif(case)
    moved = [k for k, d in deltas(case.result, after).items() if d["rank"] != 0]
    return len(moved) >= c["min"], f"{len(moved)} careers changed rank"


def whatif_component_unchanged(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    """Compares component values (0–1): rounding points to tenths can move 0.1 between components."""
    after = _require_whatif(case)
    key = c["component"]
    changed = [k for k, s in after.scores.items() if s.values[key] != case.result.scores[k].values[key]]
    return not changed, f"{key} changed for: {changed or 'none'}"


def whatif_component_not_lower(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    after = _require_whatif(case)
    key = c["component"]
    lower = [k for k, s in after.scores.items() if s.values[key] < case.result.scores[k].values[key] - 1e-9]
    return not lower, f"{key} fell for: {lower or 'none'}"


def whatif_feasible_not_more(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    after = _require_whatif(case)
    before_n = sum(f.status == "feasible" for f in case.result.finances.values())
    after_n = sum(f.status == "feasible" for f in after.finances.values())
    return after_n <= before_n, f"feasible careers {before_n} → {after_n}"


def whatif_zero_deltas(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    after = _require_whatif(case)
    nonzero = [k for k, d in deltas(case.result, after).items() if any(v != 0 for v in d.values())]
    return not nonzero, f"careers with a non-zero delta: {nonzero or 'none'}"


CHECKS: dict[str, Callable[[Case, dict[str, Any]], tuple[bool, str]]] = {
    "no_feasible_exceeds_capacity": no_feasible_exceeds_capacity,
    "career_in_top": career_in_top,
    "domain_in_top": domain_in_top,
    "top_career_domain_in": top_career_domain_in,
    "top_chosen_entry_in": top_chosen_entry_in,
    "status_is": status_is,
    "feasible_count": feasible_count,
    "all_feasible_ff_equal": all_feasible_ff_equal,
    "conflict_between": conflict_between,
    "hotspot_includes": hotspot_includes,
    "middle_path": middle_path_check,
    "stretch_options_valid": stretch_options_valid,
    "dream_alternatives": dream_alternatives_check,
    "scholarship_applied": scholarship_applied,
    "scholarship_cap_respected": scholarship_cap_respected,
    "roadmap_learning_steps": roadmap_learning_steps,
    "swot_items": swot_items,
    "scores_valid": scores_valid,
    "whatif_ff_not_higher": whatif_ff_not_higher,
    "whatif_rank_changes": whatif_rank_changes,
    "whatif_component_unchanged": whatif_component_unchanged,
    "whatif_component_not_lower": whatif_component_not_lower,
    "whatif_feasible_not_more": whatif_feasible_not_more,
    "whatif_zero_deltas": whatif_zero_deltas,
}


def run_scenarios(data: Dataset, group: str = "scenarios") -> list[dict[str, Any]]:
    spec = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    results = []
    for scenario in spec[group]:
        case = Case(scenario, data)
        checks = []
        for constraint in scenario["constraints"]:
            passed, detail = CHECKS[constraint["check"]](case, constraint)
            checks.append({"check": constraint["check"], "passed": passed, "detail": detail})
        results.append({"id": scenario["id"], "description": scenario["description"], "checks": checks,
                        "passed": all(c["passed"] for c in checks)})
    return results


def run_properties() -> list[dict[str, Any]]:
    results = []
    for prop in PROPERTIES:
        count = 0

        def tick() -> None:
            nonlocal count
            count += 1

        try:
            hypothesis_test(prop, tick)()
            passed, error = True, ""
        except Exception as exc:  # a failing property raises; record it instead of stopping
            passed, error = False, str(exc).splitlines()[0]
        results.append({"name": prop.name, "examples": count, "passed": passed, "error": error})
    return results


def write_report(
    scenarios: list[dict[str, Any]], tracked: list[dict[str, Any]], properties: list[dict[str, Any]], data: Dataset
) -> str:
    n_checks = sum(len(s["checks"]) for s in scenarios)
    n_checks_ok = sum(c["passed"] for s in scenarios for c in s["checks"])
    n_ok = sum(s["passed"] for s in scenarios)
    props_ok = sum(p["passed"] for p in properties)
    profiles = sum(p["examples"] for p in properties)
    lines = [
        "# PRISM Engine benchmark",
        "",
        f"Generated by `python scripts/benchmark.py` on {date.today().isoformat()}. "
        "Every number below is counted by the script; nothing is typed in by hand.",
        "",
        "## Summary",
        "",
        f"- Scenarios passed: **{n_ok} / {len(scenarios)}** ({n_checks_ok} / {n_checks} constraints)",
        f"- Properties passed: **{props_ok} / {len(properties)}**",
        f"- Random profiles tested: **{profiles:,}** ({len(properties)} properties × up to "
        f"{MAX_EXAMPLES:,} examples, hypothesis seed {SEED})",
        f"- Dataset: {len(data.careers)} careers, {len(data.scholarships)} scholarships, {len(data.exams)} exams",
        "",
        "Scenarios check rules only (for example \"no feasible career exceeds capacity\"); "
        "they never compare against stored scores.",
        "",
        "Until System 1 is built, each scenario gives the student's domain affinity and the parent's concerns as "
        "inputs (stand-ins for the System 1 output). pipeline.py and whatif.py come in later phases, "
        "so the engine stages are chained by `tests/engine_chain.py`.",
        "",
        "## Properties (§16)",
        "",
        "| Property | Random profiles | Result |",
        "|---|---|---|",
    ]
    for p in properties:
        result = "passed" if p["passed"] else f"failed: {p['error']}"
        lines.append(f"| {p['name']} | {p['examples']:,} | {result} |")
    lines += ["", "## Scenarios", "", "| Scenario | Constraints passed | Result |", "|---|---|---|"]
    for s in scenarios:
        ok = sum(c["passed"] for c in s["checks"])
        lines.append(f"| {s['id']}: {s['description']} | {ok} / {len(s['checks'])} | "
                     f"{'passed' if s['passed'] else 'failed'} |")
    lines += ["", "## Tracked persona stories (not counted)", "",
              "§14 says persona answers are tuned after Phase 4 so each story holds. These checks are "
              "reported now so the gap is visible.", "",
              "| Story | Constraints holding | Detail |", "|---|---|---|"]
    for s in tracked:
        ok = sum(c["passed"] for c in s["checks"])
        detail = "; ".join(c["detail"] for c in s["checks"] if not c["passed"]) or "holds"
        lines.append(f"| {s['id']}: {s['description']} | {ok} / {len(s['checks'])} | {detail} |")
    failed = [(s, c) for s in scenarios for c in s["checks"] if not c["passed"]]
    if failed:
        lines += ["", "## Failed constraints", ""]
        lines += [f"- {s['id']} / {c['check']}: {c['detail']}" for s, c in failed]
    report = "\n".join(lines) + "\n"
    OUTPUT.write_text(report, encoding="utf-8")
    return report


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # Windows consoles default to cp1252
    data = get_dataset()
    scenarios = run_scenarios(data)
    tracked = run_scenarios(data, "tracked")
    for s in scenarios + tracked:
        print(f"{'PASS' if s['passed'] else 'FAIL'}  {s['id']}")
        for c in s["checks"]:
            print(f"      {'ok ' if c['passed'] else 'NO '} {c['check']}: {c['detail']}")
    properties = run_properties()
    report = write_report(scenarios, tracked, properties, data)
    print()
    print(report)
    all_ok = all(s["passed"] for s in scenarios) and all(p["passed"] for p in properties)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
