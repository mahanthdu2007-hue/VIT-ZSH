"""§12 template explanations: built only from engine values, for the top 5 careers and the middle path."""

import pytest
from strategies import AS_OF, DATA, stand_in_decisions

from app.engine import config
from app.engine.formatting import format_inr
from app.engine.pipeline import run_pipeline
from app.rag.templates import explained_ids, template_explanations

CITY_NAMES = {c.id: c.name for c in DATA.cities}


@pytest.mark.parametrize(("amount", "text"), [
    (0, "₹0"), (500, "₹500"), (5_000, "₹5,000"), (50_000, "₹50,000"), (500_000, "₹5,00,000"),
    (1_250_000, "₹12,50,000"), (15_000_000, "₹1,50,00,000"), (-300_000, "-₹3,00,000"),
])
def test_format_inr_uses_indian_grouping(amount: int, text: str) -> None:
    assert format_inr(amount) == text


@pytest.mark.parametrize("profile_id", ["ananya", "rahul", "meera"])
def test_explanations_for_top_five_and_middle_path(profile_id: str) -> None:
    profile = next(p for p in DATA.demo_profiles if p.id == profile_id)
    decisions = stand_in_decisions(dict.fromkeys(config.DOMAINS, 0.3), {})
    result = run_pipeline(profile.student, profile.parent, DATA, AS_OF, decisions=decisions)
    explanations = template_explanations(result, CITY_NAMES, profile.student.home_city,
                                         profile.parent.annual_income_inr)
    ids = [r.career_id for r in result.ranking[:5]]
    if result.middle_path and result.middle_path.career_id not in ids:
        ids.append(result.middle_path.career_id)
    assert explained_ids(result) == ids == [e.career_id for e in explanations.items]
    assert explanations.source == "template"
    for item in explanations.items:
        detail = result.details[item.career_id]
        assert len(item.why) == config.EXPLAIN_WHY_COUNT
        assert len(item.why_not) == config.EXPLAIN_WHY_NOT_COUNT
        assert item.cited_ids[:2] == [detail.career.id, detail.pathway.id]
        assert format_inr(detail.finance.effective_cost or 0) in item.roadmap_narrative
        assert "indicative estimate" in item.roadmap_narrative
        assert detail.pathway.label in item.roadmap_narrative
        top_component = max(config.SCORE_POINTS, key=lambda k: detail.score.values[k])
        label = config.COMPONENT_LABELS[top_component]
        assert f"{label} {detail.score.points[top_component]:.1f} of" in item.why[0]
