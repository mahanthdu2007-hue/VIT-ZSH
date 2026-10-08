import pytest
from factories import career, finance, parent, pathway, scholarship, school_student

from app.engine.alternatives import dream_alternatives, stretch_options
from app.engine.scoring import prism_score
from app.engine.solver import solve_career
from app.models.schemas import StudentFit

VALUES = {"student_fit": 0.5, "financial_fit": 0.5, "market_demand": 0.5, "growth": 0.5, "parent_alignment": 0.5}


def score(career_id: str, sf: float):  # type: ignore[no-untyped-def]
    return prism_score(career_id, VALUES | {"student_fit": sf})


def fit(career_id: str, sf: float) -> StudentFit:
    return StudentFit(career_id=career_id, centred_cosine=0.5, domain_affinity=0.0, academic_alignment=0.5,
                      student_fit=sf)


DREAM = career([pathway("a"), pathway("b")], fields={"id": "dream", "adjacent_careers": ["x", "y", "z"]})
CAREERS = {"dream": DREAM}
SCORES = {"dream": score("dream", 0.9), "x": score("x", 0.4), "y": score("y", 0.8), "z": score("z", 0.6)}


def test_dream_needs_aid_ranks_adjacent_by_score() -> None:
    finances = {c: finance(c) for c in SCORES} | {"dream": finance("dream", "needs_aid")}
    result = dream_alternatives("dream", CAREERS, finances, SCORES, ["y", "z", "x"])
    assert result is not None and result.reason == "needs_aid"
    assert [a.career_id for a in result.alternatives] == ["y", "z", "x"]


def test_dream_outside_top_five() -> None:
    finances = {c: finance(c) for c in SCORES}
    top = ["a", "b", "c", "d", "e", "dream"]
    result = dream_alternatives("dream", CAREERS, finances, SCORES, top)
    assert result is not None and result.reason == "outside_top"


def test_no_alternatives_when_dream_is_in_top_five_or_unset() -> None:
    finances = {c: finance(c) for c in SCORES}
    assert dream_alternatives("dream", CAREERS, finances, SCORES, ["x", "dream"]) is None
    assert dream_alternatives(None, CAREERS, finances, SCORES, []) is None


def test_stretch_options_top_quartile_needs_aid_with_aid() -> None:
    # SF: a 0.9 (needs aid), b 0.8, c 0.5 (needs aid), d 0.3. 75th percentile of
    # [0.3, 0.5, 0.8, 0.9] (linear) = 0.8 + 0.25 × 0.1 = 0.825 → only a qualifies.
    cheap = pathway("cheap", cost=(200000, 400000))
    pricey = pathway("pricey", cost=(800000, 1200000), institution="private")
    a = career([cheap, pricey], fields={"id": "a", "adjacent_careers": ["b", "c", "d"]})
    c = career([cheap, pricey], fields={"id": "c"})
    schemes = [scholarship("open", 10000, ["ug"], income_max=200000),       # income too high → ineligible
               scholarship("girls", 50000, ["ug"], restricted_to="girls"),  # restricted, still shown as aid
               scholarship("merit", 20000, ["ug"])]
    p = parent(700000, 100000)
    finances = {"a": solve_career(a, school_student(), p, schemes), "b": finance("b"),
                "c": solve_career(c, school_student(), p, schemes), "d": finance("d")}
    fits = {"a": fit("a", 0.9), "b": fit("b", 0.8), "c": fit("c", 0.5), "d": fit("d", 0.3)}
    options = stretch_options({"a": a, "c": c}, finances, fits, schemes, 700000)

    assert [o.career_id for o in options] == ["a"]
    option = options[0]
    # merit 20,000 × 4 = 80,000 counted → cheap effective 2,20,000; gap vs capacity 1,00,000 = 1,20,000
    assert (option.cheapest_pathway_id, option.funding_gap) == ("cheap", 120000)
    assert [s.scholarship_id for s in option.scholarships] == ["girls", "merit"]
    # pricey: 10,00,000 − 80,000 = 9,20,000 effective → gap 8,20,000
    assert [(p.pathway_id, p.funding_gap) for p in option.cheaper_pathways] == [
        ("cheap", 120000), ("pricey", 820000)]
    assert option.adjacent_feasible == ["b", "d"]
    assert option.student_fit == pytest.approx(0.9)
