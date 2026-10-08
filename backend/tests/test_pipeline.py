"""§7 pipeline: every stage is traced, outputs are consistent with the trace, and runs are deterministic."""

from datetime import date

import pytest
from strategies import AS_OF, DATA, stand_in_decisions

from app.engine import config
from app.engine.pipeline import run_pipeline
from app.engine.system1 import KeywordBackend
from app.models.schemas import PipelineResult

ANANYA = next(p for p in DATA.demo_profiles if p.id == "ananya")
AFFINITY = dict.fromkeys(config.DOMAINS, 0.05) | {"Technology": 0.9, "Engineering": 0.4}
CONCERNS = dict.fromkeys(config.PARENT_CONCERNS, 0.1) | {"financial burden": 0.8}


def run(as_of: date = AS_OF) -> PipelineResult:
    return run_pipeline(ANANYA.student, ANANYA.parent, DATA, as_of,
                        decisions=stand_in_decisions(AFFINITY, CONCERNS))


def test_trace_covers_every_stage_for_every_career() -> None:
    trace = run().trace
    n = len(DATA.careers)
    assert trace.ingest.track == "school"
    assert 0 < trace.ingest.completeness.score <= 1
    assert set(trace.vectorize.student_vector.values) == set(config.STUDENT_DIMENSIONS)
    assert [d.question_id for d in trace.system1.decisions] == [config.DECISION_STUDENT_DOMAIN,
                                                                config.DECISION_PARENT_CONCERNS]
    assert trace.system1.domain_affinity == AFFINITY
    assert trace.system1.parent_concerns == CONCERNS
    assert trace.system1.reused
    assert trace.solver.capacity == 750_000
    assert trace.solver.loan_factor == 0.5
    for stage in (trace.solver.finances, trace.matcher.fits, trace.conflict.parent_alignment,
                  trace.market.markets, trace.scoring.growth, trace.scoring.scores, trace.scoring.confidence):
        assert len(stage) == n
    assert trace.conflict.concern_weights["financial_fit"] > trace.conflict.concern_weights["domain"]


def test_outputs_match_the_trace() -> None:
    result = run()
    trace = result.trace
    scores = {s.career_id: s for s in trace.scoring.scores}
    assert [r.career_id for r in result.ranking] == trace.ranking.top_career_ids == trace.ranking.order[:10]
    assert [r.rank for r in result.ranking] == list(range(1, len(result.ranking) + 1))
    for ranked in result.ranking:
        assert ranked.score == scores[ranked.career_id].score
        assert ranked.points == scores[ranked.career_id].points
    assert result.conflict == trace.conflict.conflict
    assert result.middle_path == trace.conflict.middle_path
    assert [o.career_id for o in result.stretch_options] == trace.ranking.stretch_career_ids
    statuses = {f.career_id: f.status for f in trace.solver.finances}
    assert all(statuses[c] == "feasible" for c in trace.ranking.order)
    scored = [scores[c].score for c in trace.ranking.order]
    assert scored == sorted(scored, reverse=True)


def test_details_cover_top_careers_middle_path_and_stretch_options() -> None:
    result = run()
    expected = {r.career_id for r in result.ranking} | {o.career_id for o in result.stretch_options}
    if result.middle_path:
        expected.add(result.middle_path.career_id)
    assert expected <= set(result.details)
    top = result.details[result.ranking[0].career_id]
    assert top.rank == 1
    assert top.pathway.id == top.finance.chosen_pathway_id
    assert top.skill_plan.career_id == top.career.id
    assert [e.id for e in top.exams] == [e for e in top.pathway.entrance_exams if e in {x.id for x in DATA.exams}]
    assert result.confidence == top.confidence
    assert result.swot is not None and result.swot.threats[0].label == top.career.name


def test_timeline_and_exams_follow_the_as_of_date() -> None:
    one, two = run(date(2026, 10, 8)), run(date(2027, 3, 1))
    top = one.ranking[0].career_id
    assert one.details[top].skill_plan.timeline[0].year == 2026
    assert two.details[top].skill_plan.timeline[0].year == 2027
    assert one.as_of == date(2026, 10, 8)


def test_identical_input_gives_identical_output() -> None:
    assert run().model_dump() == run().model_dump()
    first = run_pipeline(ANANYA.student, ANANYA.parent, DATA, AS_OF, model=KeywordBackend())
    second = run_pipeline(ANANYA.student, ANANYA.parent, DATA, AS_OF, model=KeywordBackend())
    assert first.model_dump() == second.model_dump()


def test_stage_3_runs_the_model_when_no_decisions_are_given() -> None:
    result = run_pipeline(ANANYA.student, ANANYA.parent, DATA, AS_OF, model=KeywordBackend())
    assert result.trace.system1.backend == "keyword"
    assert not result.trace.system1.reused
    assert result.trace.system1.domain_affinity["Technology"] == config.KEYWORD_CONFIDENCE_CAP


def test_model_and_decisions_are_exclusive() -> None:
    with pytest.raises(ValueError):
        run_pipeline(ANANYA.student, ANANYA.parent, DATA, AS_OF)
    with pytest.raises(ValueError):
        run_pipeline(ANANYA.student, ANANYA.parent, DATA, AS_OF, model=KeywordBackend(),
                     decisions=stand_in_decisions(AFFINITY, CONCERNS))
