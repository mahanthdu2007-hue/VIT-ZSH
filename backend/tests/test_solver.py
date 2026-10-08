import pytest
from factories import career, college_student, parent, pathway, scholarship, school_student

from app.engine.loader import get_dataset
from app.engine.solver import (
    candidate_entries,
    capacity,
    expected_scholarship,
    financial_fit,
    solve_all,
    solve_career,
)

# A test career with one pathway of each kind (costs are total, cost_mid in brackets):
#   govt     after_class_12  2,00,000–4,00,000   (3,00,000)  quality 0.80  4 years
#   private  after_class_12  8,00,000–12,00,000  (10,00,000) quality 0.65  4 years
#   diploma  after_class_10  60,000–1,00,000     (80,000)    quality 0.55  3 years
#   lateral  graduate        1,00,000–2,00,000   (1,50,000)  quality 0.85  2 years
GOVT = pathway("govt", cost=(200000, 400000), quality=0.8, duration=4)
PRIVATE = pathway("private", cost=(800000, 1200000), quality=0.65, duration=4, institution="private")
DIPLOMA = pathway("diploma", "after_class_10", (60000, 100000), 0.55, 3, "diploma")
LATERAL = pathway("lateral", "graduate", (100000, 200000), 0.85, 2)
CAREER = career([GOVT, PRIVATE, DIPLOMA, LATERAL])

OPEN_UG_PG = scholarship("open_ug_pg", 12000, ["ug", "pg"], income_max=450000)
GIRLS_ONLY = scholarship("girls_only", 50000, ["ug", "pg"], income_max=800000, restricted_to="girls")
DIPLOMA_MERIT = scholarship("diploma_merit", 30000, ["diploma"])
SCHOLARSHIPS = [OPEN_UG_PG, GIRLS_ONLY, DIPLOMA_MERIT]


def by_id(result, pathway_id):  # type: ignore[no-untyped-def]
    return next(p for p in result.pathways if p.pathway_id == pathway_id)


def test_capacity_uses_loan_factor() -> None:
    assert capacity(parent(1, 500000, "none")) == 500000
    assert capacity(parent(1, 500000, "moderate")) == 750000
    assert capacity(parent(1, 500000, "high")) == 1000000


def test_case_a_within_budget_class_12() -> None:
    # Income 7,00,000 > 4,50,000, so no scholarship. Capacity = 5,00,000 × 1.5 = 7,50,000.
    # govt: objective = 0.80 − 0.6 × 3,00,000 / 7,50,000 = 0.56, feasible.
    # private: objective = 0.65 − 0.6 × 10,00,000 / 7,50,000 = −0.15, infeasible.
    result = solve_career(CAREER, school_student(12), parent(700000, 500000, "moderate"), SCHOLARSHIPS)
    assert (result.status, result.chosen_pathway_id, result.financial_fit) == ("feasible", "govt", 1.0)
    assert result.capacity == 750000 and result.funding_gap == 0
    assert by_id(result, "govt").objective == pytest.approx(0.56)
    assert by_id(result, "private").objective == pytest.approx(-0.15)
    assert not by_id(result, "private").feasible
    assert by_id(result, "diploma").stage_fit is False and by_id(result, "diploma").objective is None


def test_case_b_every_pathway_unaffordable_needs_aid() -> None:
    # Income 3,00,000 → open scheme: 12,000 × 4 = 48,000 (cap 1,80,000 not reached).
    # govt effective = 2,52,000; private = 9,52,000. Capacity = 2,00,000 (no loan).
    # Both exceed capacity → needs_aid, cheapest = govt, gap = 2,52,000 − 2,00,000 = 52,000.
    result = solve_career(CAREER, school_student(12), parent(300000, 200000), SCHOLARSHIPS)
    assert result.status == "needs_aid"
    assert (result.chosen_pathway_id, result.effective_cost) == ("govt", 252000)
    assert (result.funding_gap, result.financial_fit) == (52000, 0.0)
    assert by_id(result, "govt").scholarship_id == "open_ug_pg"


def test_case_c_partial_financial_fit_with_loan() -> None:
    # Budget 2,50,000, high loan → capacity 5,00,000. govt effective 3,00,000 is above budget.
    # FF = 1 − 0.5 × (3,00,000 − 2,50,000) / (5,00,000 − 2,50,000) = 0.9.
    # objective = 0.80 − 0.6 × 3,00,000 / 5,00,000 = 0.44.
    result = solve_career(CAREER, school_student(12), parent(700000, 250000, "high"), SCHOLARSHIPS)
    assert (result.status, result.chosen_pathway_id) == ("feasible", "govt")
    assert result.financial_fit == pytest.approx(0.9)
    assert by_id(result, "govt").objective == pytest.approx(0.44)


def test_case_d_scholarship_capped_at_sixty_percent() -> None:
    # Class 10 → after_class_10 and after_class_12 pathways are candidates.
    # diploma: merit scheme 30,000 × 3 = 90,000 > cap 0.6 × 80,000 = 48,000 → 48,000.
    # effective = 32,000; capacity 1,00,000; objective = 0.55 − 0.6 × 32,000 / 1,00,000 = 0.358.
    result = solve_career(CAREER, school_student(10), parent(300000, 100000), SCHOLARSHIPS)
    diploma = by_id(result, "diploma")
    assert (diploma.scholarship, diploma.scholarship_capped, diploma.effective_cost) == (48000, True, 32000)
    assert diploma.objective == pytest.approx(0.358)
    assert (result.status, result.chosen_pathway_id, result.financial_fit) == ("feasible", "diploma", 1.0)


def test_case_e_college_student_only_gets_graduate_pathways() -> None:
    # lateral: open scheme at PG level 12,000 × 2 = 24,000 → effective 1,26,000.
    # capacity 1,50,000; objective = 0.85 − 0.6 × 1,26,000 / 1,50,000 = 0.346.
    result = solve_career(CAREER, college_student(), parent(300000, 150000), SCHOLARSHIPS)
    assert [p.pathway_id for p in result.pathways if p.stage_fit] == ["lateral"]
    assert (result.chosen_pathway_id, result.effective_cost) == ("lateral", 126000)
    assert by_id(result, "lateral").objective == pytest.approx(0.346)


def test_milp_prefers_higher_objective_not_just_cheapest() -> None:
    # Capacity 20,00,000: govt objective 0.80 − 0.09 = 0.71; best objective 0.95 − 0.12 = 0.83.
    best = pathway("best", cost=(300000, 500000), quality=0.95)
    result = solve_career(career([GOVT, PRIVATE, best]), school_student(12),
                          parent(700000, 2000000), SCHOLARSHIPS)
    assert result.chosen_pathway_id == "best"
    assert by_id(result, "best").objective == pytest.approx(0.83)
    assert by_id(result, "govt").objective == pytest.approx(0.71)


def test_exact_objective_tie_prefers_higher_quality_in_any_order() -> None:
    # Capacity 4,50,000: govt 0.80 − 0.6 × 3,50,000 / 4,50,000 = 0.3333…
    #                    online 0.70 − 0.6 × 2,75,000 / 4,50,000 = 0.3333… (exact tie)
    govt = pathway("govt", cost=(200000, 500000), quality=0.8)
    online = pathway("online", cost=(150000, 400000), quality=0.7, institution="online")
    for order in ([govt, online], [online, govt]):
        result = solve_career(career(order), school_student(12),
                              parent(700000, 300000, "moderate"), SCHOLARSHIPS)
        assert by_id(result, "govt").objective == pytest.approx(by_id(result, "online").objective)
        assert result.chosen_pathway_id == "govt"


def test_financial_fit_uses_the_cheapest_candidate_pathway() -> None:
    # Budget 3,00,000, capacity 4,50,000. The solver picks govt (3,50,000), but the online
    # route costs 2,75,000 ≤ budget, so FF = 1.0 (govt alone would give 1 − 0.5 × 0.5/1.5 = 0.833).
    govt = pathway("govt", cost=(200000, 500000), quality=0.8)
    online = pathway("online", cost=(150000, 400000), quality=0.7, institution="online")
    result = solve_career(career([govt, online]), school_student(12), parent(700000, 300000, "moderate"), [])
    assert (result.chosen_pathway_id, result.effective_cost, result.financial_fit) == ("govt", 350000, 1.0)
    # Budget 2,00,000, capacity 3,00,000: only online fits → FF = 1 − 0.5 × 75,000 / 1,00,000 = 0.625.
    lower = solve_career(career([govt, online]), school_student(12), parent(700000, 200000, "moderate"), [])
    assert (lower.chosen_pathway_id, lower.financial_fit) == ("online", pytest.approx(0.625))


def test_zero_budget_is_needs_aid_with_full_gap() -> None:
    result = solve_career(CAREER, school_student(12), parent(700000, 0, "high"), SCHOLARSHIPS)
    assert result.capacity == 0
    assert (result.status, result.chosen_pathway_id, result.funding_gap) == ("needs_aid", "govt", 300000)
    assert by_id(result, "govt").objective is None


def test_zero_budget_with_free_pathway_is_feasible() -> None:
    free = pathway("free", cost=(0, 0), quality=0.5)
    result = solve_career(career([free, GOVT]), school_student(12), parent(700000, 0), SCHOLARSHIPS)
    assert (result.status, result.chosen_pathway_id, result.financial_fit) == ("feasible", "free", 1.0)
    assert by_id(result, "free").objective == 0.5


def test_no_loan_capacity_equals_budget_boundary() -> None:
    # Capacity == budget: cost exactly at budget is feasible with FF 1; one rupee over is needs_aid.
    at_budget = solve_career(CAREER, school_student(12), parent(700000, 300000), SCHOLARSHIPS)
    over = solve_career(CAREER, school_student(12), parent(700000, 299999), SCHOLARSHIPS)
    assert (at_budget.status, at_budget.financial_fit) == ("feasible", 1.0)
    assert (over.status, over.financial_fit, over.funding_gap) == ("needs_aid", 0.0, 1)


def test_financial_fit_never_divides_when_capacity_equals_budget() -> None:
    assert financial_fit(300000, 300000, 300000) == 1.0
    assert financial_fit(300001, 300000, 300000) == 0.0


def test_restricted_and_online_pathways_get_no_scholarship() -> None:
    online = pathway("online", cost=(100000, 200000), institution="online")
    assert expected_scholarship(GOVT, CAREER, 300000, [GIRLS_ONLY]) == (0, None, False)
    assert expected_scholarship(online, CAREER, 300000, [OPEN_UG_PG]) == (0, None, False)
    assert expected_scholarship(GOVT, CAREER, 300000, [OPEN_UG_PG]) == (48000, "open_ug_pg", False)


def test_scholarship_requires_matching_domain_and_income() -> None:
    health_only = scholarship("health", 20000, ["ug"], domains=["Health"])
    assert expected_scholarship(GOVT, CAREER, 300000, [health_only])[0] == 0
    assert expected_scholarship(GOVT, CAREER, 450001, [OPEN_UG_PG])[0] == 0
    assert expected_scholarship(GOVT, CAREER, 450000, [OPEN_UG_PG])[0] == 48000


@pytest.mark.parametrize(
    ("student", "entries"),
    [
        (school_student(9), ("after_class_10", "after_class_12")),
        (school_student(10), ("after_class_10", "after_class_12")),
        (school_student(11), ("after_class_12",)),
        (school_student(12), ("after_class_12",)),
        (college_student(), ("graduate",)),
    ],
)
def test_pathway_filtering_by_stage(student, entries) -> None:  # type: ignore[no-untyped-def]
    assert candidate_entries(student) == entries


def test_career_without_a_pathway_for_the_stage() -> None:
    clinical = career([GOVT, PRIVATE])  # no graduate pathway
    result = solve_career(clinical, college_student(), parent(700000, 5000000), SCHOLARSHIPS)
    assert (result.status, result.chosen_pathway_id, result.financial_fit) == ("no_pathway", None, 0.0)


def test_one_combined_milp_matches_solving_each_career_alone() -> None:
    data = get_dataset()
    for profile in data.demo_profiles:
        for budget in (0, 150000, 300000, 500000, 1000000):
            family = profile.parent.model_copy(update={"education_budget_inr": budget})
            together = solve_all(data.careers, profile.student, family, data.scholarships)
            alone = [solve_career(c, profile.student, family, data.scholarships) for c in data.careers]
            assert together == alone
