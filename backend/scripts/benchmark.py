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

from strategies import AS_OF, stand_in_decisions  # noqa: E402
from test_properties import MAX_EXAMPLES, PROPERTIES, SEED, hypothesis_test  # noqa: E402

from app.engine import config  # noqa: E402
from app.engine.loader import get_dataset  # noqa: E402
from app.engine.pipeline import run_pipeline  # noqa: E402
from app.engine.solver import capacity  # noqa: E402
from app.engine.system1 import DecisionModel, get_decision_model  # noqa: E402
from app.engine.whatif import apply_overrides, run_whatif  # noqa: E402
from pydantic import TypeAdapter  # noqa: E402

from app.models.schemas import (  # noqa: E402
    CareerFinance,
    Dataset,
    ParentInput,
    PipelineResult,
    PrismScore,
    StudentInput,
    WhatIfOverrides,
    WhatIfResult,
)

SCENARIOS = TESTS / "benchmark_scenarios.json"
OUTPUT = BACKEND.parent / "docs" / "BENCHMARK.md"
POINTS_TOLERANCE = 0.1  # §16
STUDENT_ADAPTER: TypeAdapter[StudentInput] = TypeAdapter(StudentInput)


def finances_of(result: PipelineResult) -> dict[str, CareerFinance]:
    return {f.career_id: f for f in result.trace.solver.finances}


def scores_of(result: PipelineResult) -> dict[str, PrismScore]:
    return {s.career_id: s for s in result.trace.scoring.scores}


class Case:
    """One scenario's inputs and pipeline result, plus the What-If re-run if the scenario has overrides.

    Scenarios with a domain_affinity block use stand-in System 1 probabilities; the others run the full
    pipeline, including the real System 1 backend.
    """

    def __init__(self, scenario: dict[str, Any], data: Dataset, model: DecisionModel) -> None:
        self.data = data
        self.careers = {c.id: c for c in data.careers}
        self.student, self.parent = build_inputs(scenario["profile"], data)
        if "domain_affinity" in scenario:
            affinity = dict.fromkeys(config.DOMAINS, 0.0) | scenario["domain_affinity"]
            decisions = stand_in_decisions(affinity, scenario.get("parent_concerns", {}))
            self.result = run_pipeline(self.student, self.parent, data, AS_OF, decisions=decisions)
        else:
            self.result = run_pipeline(self.student, self.parent, data, AS_OF, model=model)
        self.decisions = self.result.trace.system1.decisions
        self.finances = finances_of(self.result)
        self.scores = scores_of(self.result)
        self.whatif: WhatIfResult | None = None
        self.after: PipelineResult | None = None
        if "whatif" in scenario:
            self.overrides = WhatIfOverrides.model_validate(scenario["whatif"])
            self.whatif = run_whatif(self.student, self.parent, self.decisions, self.overrides, data, AS_OF)
            student, parent = apply_overrides(self.student, self.parent, self.overrides)
            self.after = run_pipeline(student, parent, data, AS_OF, decisions=self.decisions)

    def top(self, n: int) -> list[str]:
        return [s.career_id for s in self.result.ranking[:n]]


def build_inputs(profile: dict[str, Any], data: Dataset) -> tuple[StudentInput, ParentInput]:
    """A demo profile with the scenario's field overrides applied (validated again)."""
    demo = next(p for p in data.demo_profiles if p.id == profile["demo"])
    student = STUDENT_ADAPTER.validate_python(demo.student.model_dump() | profile.get("student", {}))
    parent = ParentInput.model_validate(demo.parent.model_dump() | profile.get("parent", {}))
    return student, parent


def _require_whatif(case: Case) -> tuple[WhatIfResult, PipelineResult]:
    if case.whatif is None or case.after is None:
        raise ValueError("this check needs a 'whatif' block in the scenario")
    return case.whatif, case.after


def no_feasible_exceeds_capacity(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    cap = capacity(case.parent)
    over = [f.career_id for f in case.finances.values()
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
        finance = case.finances[career_id]
        entries.append(next(p.entry for p in finance.pathways if p.pathway_id == finance.chosen_pathway_id))
    return all(e in c["entries"] for e in entries), f"chosen entries of top {c['n']}: {sorted(set(entries))}"


def top_chosen_institution_in(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    kinds = [case.result.details[t].pathway.institution_type for t in case.top(c["n"])]
    found = [k for k in kinds if k in c["institutions"]]
    return len(found) >= c.get("at_least", 1), f"chosen institution types of top {c['n']}: {kinds}"


def status_is(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    status = case.finances[c["career"]].status
    return status == c["status"], f"{c['career']} is {status}"


def feasible_count(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    count = sum(f.status == "feasible" for f in case.finances.values())
    return c.get("min", 0) <= count <= c.get("max", len(case.careers)), f"{count} feasible careers"


def all_feasible_ff_equal(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    values = {round(f.financial_fit, 9) for f in case.finances.values() if f.status == "feasible"}
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
    pathway = case.result.details[mp.career_id].pathway
    ok = case.finances[mp.career_id].status == "feasible"
    if "method" in c:
        ok = ok and mp.method == c["method"]
    if c.get("both_gain"):
        ok = ok and mp.student_gain > 0 and mp.parent_gain > 0
    if "domains" in c:
        ok = ok and case.careers[mp.career_id].domain in c["domains"]
    if "institutions" in c:
        ok = ok and pathway.institution_type in c["institutions"]
    return ok, (f"{mp.career_id} ({case.careers[mp.career_id].domain}, {pathway.institution_type} pathway) via "
                f"{mp.method}; gains student {mp.student_gain:+.3f}, parent {mp.parent_gain:+.3f}")


def stretch_options_valid(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    options = case.result.stretch_options
    all_need_aid = all(case.finances[o.career_id].status == "needs_aid" for o in options)
    with_aid = all(o.cheaper_pathways for o in options)
    return (all_need_aid and with_aid and c.get("min", 0) <= len(options) <= c.get("max", len(case.careers)),
            f"{len(options)} stretch options: {[o.career_id for o in options][:5]}")


def dream_alternatives_check(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    dream = case.result.alternatives
    if c.get("reason") is None:
        return dream is None, f"dream alternatives: {dream.reason if dream else 'none'}"
    ok = dream is not None and dream.reason == c["reason"] and bool(dream.alternatives)
    shown = [a.career_id for a in dream.alternatives] if dream else []
    return ok, f"dream alternatives: {dream.reason if dream else 'none'}, {shown}"


def scholarship_applied(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    used = sorted({e.scholarship_id for f in case.finances.values() for e in f.pathways
                   if e.scholarship > 0 and e.scholarship_id})
    return len(used) >= c["min"], f"{len(used)} schemes lower a pathway cost: {used[:5]}"


def scholarship_cap_respected(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    over = [(f.career_id, e.pathway_id) for f in case.finances.values() for e in f.pathways
            if e.scholarship > round(config.SCHOLARSHIP_CAP_FRACTION * e.cost_mid)]
    return not over, f"pathways above the 60% cap: {over or 'none'}"


def scholarships_shown(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    """Scholarships the dashboard lists for a top career's pathway or for a stretch option."""
    shown = {s.scholarship_id for t in case.top(c["n"]) for s in case.result.details[t].scholarships}
    shown |= {s.scholarship_id for o in case.result.stretch_options for s in o.scholarships}
    return len(shown) >= c["min"], f"{len(shown)} schemes shown for the top {c['n']} and stretch options"


def roadmap_learning_steps(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    top = case.top(1)
    plan = case.result.details[top[0]].skill_plan if top else None
    steps = sum(s.kind == "learning" for s in plan.roadmap) if plan else 0
    return steps >= c["min"], f"{steps} learning steps for {plan.career_id if plan else None}"


def swot_items(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    swot = case.result.swot
    items = [o for o in (swot.opportunities if swot else []) if o.kind == c["kind"]]
    return len(items) >= c["min"], f"{len(items)} {c['kind']} opportunities: {[o.label for o in items]}"


def scores_valid(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    scores = case.scores.values()
    in_range = all(0 <= s.score <= 100 for s in scores)
    sums = all(abs(sum(s.points.values()) - s.score) <= POINTS_TOLERANCE for s in scores)
    return in_range and sums, f"{len(scores)} scores in [0, 100] with matching points: {in_range and sums}"


def whatif_ff_not_higher(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    _, after = _require_whatif(case)
    raised = [k for k, f in finances_of(after).items() if f.financial_fit > case.finances[k].financial_fit + 1e-9]
    return not raised, f"careers whose FF rose: {raised or 'none'}"


def whatif_rank_changes(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    whatif, _ = _require_whatif(case)
    moved = [ch.career_id for ch in whatif.changes if ch.rank_before != ch.rank_after]
    return len(moved) >= c["min"], f"{len(moved)} careers changed rank"


def whatif_top_changes(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    """The top-n list itself changes (order or membership), so the re-rank is visible."""
    whatif, _ = _require_whatif(case)
    before, after = case.top(c["n"]), [r.career_id for r in whatif.ranking[:c["n"]]]
    return before != after, f"top {c['n']} before {before}; after {after}"


def whatif_reason_mentions(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    """At least one reason sentence, for a career in the top n before or after, names the component."""
    whatif, _ = _require_whatif(case)
    label = config.COMPONENT_LABELS[c["component"]]
    outside = c["n"] + 1
    reasons = [ch.reason for ch in whatif.changes
               if ch.reason and label in ch.reason
               and min(ch.rank_before or outside, ch.rank_after or outside) <= c["n"]]
    return bool(reasons), f"{len(reasons)} reasons name {label}: {reasons[:1]}"


def whatif_latency(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    """§11 What-If time over repeated runs; the scenario's own What-If was the warm-up run."""
    _require_whatif(case)
    times = sorted(run_whatif(case.student, case.parent, case.decisions, case.overrides, case.data, AS_OF).elapsed_ms
                   for _ in range(c["runs"]))
    median, worst = times[len(times) // 2], times[-1]
    return worst < c["max_ms"], f"median {median:.0f} ms, slowest {worst:.0f} ms over {c['runs']} runs"


def whatif_component_unchanged(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    """Compares component values (0–1): rounding points to tenths can move 0.1 between components."""
    _, after = _require_whatif(case)
    key = c["component"]
    changed = [k for k, s in scores_of(after).items() if s.values[key] != case.scores[k].values[key]]
    return not changed, f"{key} changed for: {changed or 'none'}"


def whatif_component_not_lower(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    _, after = _require_whatif(case)
    key = c["component"]
    lower = [k for k, s in scores_of(after).items() if s.values[key] < case.scores[k].values[key] - 1e-9]
    return not lower, f"{key} fell for: {lower or 'none'}"


def whatif_feasible_not_more(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    _, after = _require_whatif(case)
    before_n = sum(f.status == "feasible" for f in case.finances.values())
    after_n = sum(f.status == "feasible" for f in finances_of(after).values())
    return after_n <= before_n, f"feasible careers {before_n} → {after_n}"


def whatif_zero_deltas(case: Case, c: dict[str, Any]) -> tuple[bool, str]:
    whatif, _ = _require_whatif(case)
    nonzero = [ch.career_id for ch in whatif.changes
               if ch.score_delta != 0 or ch.rank_before != ch.rank_after or any(ch.point_deltas.values())]
    return not nonzero, f"careers with a non-zero delta: {nonzero or 'none'}"


CHECKS: dict[str, Callable[[Case, dict[str, Any]], tuple[bool, str]]] = {
    "no_feasible_exceeds_capacity": no_feasible_exceeds_capacity,
    "career_in_top": career_in_top,
    "domain_in_top": domain_in_top,
    "top_career_domain_in": top_career_domain_in,
    "top_chosen_entry_in": top_chosen_entry_in,
    "top_chosen_institution_in": top_chosen_institution_in,
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
    "scholarships_shown": scholarships_shown,
    "roadmap_learning_steps": roadmap_learning_steps,
    "swot_items": swot_items,
    "scores_valid": scores_valid,
    "whatif_ff_not_higher": whatif_ff_not_higher,
    "whatif_rank_changes": whatif_rank_changes,
    "whatif_top_changes": whatif_top_changes,
    "whatif_reason_mentions": whatif_reason_mentions,
    "whatif_latency": whatif_latency,
    "whatif_component_unchanged": whatif_component_unchanged,
    "whatif_component_not_lower": whatif_component_not_lower,
    "whatif_feasible_not_more": whatif_feasible_not_more,
    "whatif_zero_deltas": whatif_zero_deltas,
}


def run_scenarios(data: Dataset, model: DecisionModel, group: str) -> list[dict[str, Any]]:
    spec = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    results = []
    for scenario in spec[group]:
        case = Case(scenario, data, model)
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


def _scenario_table(results: list[dict[str, Any]]) -> list[str]:
    lines = ["| Scenario | Constraints passed | Result |", "|---|---|---|"]
    for s in results:
        ok = sum(c["passed"] for c in s["checks"])
        lines.append(f"| {s['id']}: {s['description']} | {ok} / {len(s['checks'])} | "
                     f"{'passed' if s['passed'] else 'failed'} |")
    return lines


def _counts(results: list[dict[str, Any]]) -> str:
    n_checks = sum(len(s["checks"]) for s in results)
    n_checks_ok = sum(c["passed"] for s in results for c in s["checks"])
    return f"**{sum(s['passed'] for s in results)} / {len(results)}** ({n_checks_ok} / {n_checks} constraints)"


def write_report(
    scenarios: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    tracked: list[dict[str, Any]],
    properties: list[dict[str, Any]],
    data: Dataset,
    backend: str,
) -> str:
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
        f"- Engine scenarios passed: {_counts(scenarios)}",
        f"- Full-pipeline persona scenarios passed: {_counts(personas)}",
        f"- Properties passed: **{props_ok} / {len(properties)}**",
        f"- Random profiles tested: **{profiles:,}** ({len(properties)} properties × up to "
        f"{MAX_EXAMPLES:,} examples, hypothesis seed {SEED})",
        f"- Dataset: {len(data.careers)} careers, {len(data.scholarships)} scholarships, {len(data.exams)} exams",
        f"- System 1 backend for full-pipeline scenarios: `{backend}`",
        "",
        "Scenarios check rules only (for example \"no feasible career exceeds capacity\"); "
        "they never compare against stored scores. Every scenario runs `engine/pipeline.py`, and What-If "
        "scenarios run `engine/whatif.py`.",
        "",
        "Engine scenarios give the student's domain affinity and the parent's concerns as fixed probabilities "
        "(stand-in System 1 decisions), so they test the engine alone. Full-pipeline persona scenarios run "
        "every stage, including the System 1 backend above, on the §14 demo profiles.",
        "",
        "## Properties (§16)",
        "",
        "| Property | Random profiles | Result |",
        "|---|---|---|",
    ]
    for p in properties:
        result = "passed" if p["passed"] else f"failed: {p['error']}"
        lines.append(f"| {p['name']} | {p['examples']:,} | {result} |")
    lines += ["", "## Engine scenarios", "", *_scenario_table(scenarios)]
    lines += ["", "## Full-pipeline persona scenarios (§14)", "", *_scenario_table(personas)]
    lines += ["", "### Persona details", ""]
    lines += [f"- {s['id']} / {c['check']}: {c['detail']}" for s in personas for c in s["checks"]]
    lines += ["", "## Tracked persona stories (not counted)", "",
              "§14 story checks that do not hold with the §14 answers; see docs/DECISIONS.md.", "",
              "| Story | Constraints holding | Detail |", "|---|---|---|"]
    for s in tracked:
        ok = sum(c["passed"] for c in s["checks"])
        detail = "; ".join(c["detail"] for c in s["checks"] if not c["passed"]) or "holds"
        lines.append(f"| {s['id']}: {s['description']} | {ok} / {len(s['checks'])} | {detail} |")
    failed = [(s, c) for s in scenarios + personas for c in s["checks"] if not c["passed"]]
    if failed:
        lines += ["", "## Failed constraints", ""]
        lines += [f"- {s['id']} / {c['check']}: {c['detail']}" for s, c in failed]
    report = "\n".join(lines) + "\n"
    OUTPUT.write_text(report, encoding="utf-8")
    return report


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # Windows consoles default to cp1252
    data = get_dataset()
    model = get_decision_model()
    scenarios = run_scenarios(data, model, "scenarios")
    personas = run_scenarios(data, model, "personas")
    tracked = run_scenarios(data, model, "tracked")
    for s in scenarios + personas + tracked:
        print(f"{'PASS' if s['passed'] else 'FAIL'}  {s['id']}")
        for c in s["checks"]:
            print(f"      {'ok ' if c['passed'] else 'NO '} {c['check']}: {c['detail']}")
    properties = run_properties()
    report = write_report(scenarios, personas, tracked, properties, data, model.name)
    print()
    print(report)
    all_ok = all(s["passed"] for s in scenarios + personas) and all(p["passed"] for p in properties)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
