import pytest
from factories import career, pathway, school_student

from app.engine import config
from app.engine.market import market_demand, reachable_cities

DEMAND = {c: 0.5 for c in config.CITIES} | {"mysuru": 0.35, "bengaluru": 0.95, "hyderabad": 0.85}
CAREER = career([pathway("a"), pathway("b")],
                fields={"city_demand": DEMAND, "job_velocity": 0.8, "disruption_index": 0.25})


def test_not_relocating_uses_home_city() -> None:
    # MD = 0.5 × 0.35 + 0.3 × 0.8 + 0.2 × 0.75 = 0.565
    result = market_demand(CAREER, school_student(home_city="mysuru"))
    assert (result.best_city, result.local_demand) == ("mysuru", 0.35)
    assert result.market_demand == pytest.approx(0.565)


def test_relocating_uses_best_preferred_city() -> None:
    # MD = 0.5 × 0.95 + 0.24 + 0.15 = 0.865
    student = school_student(willing_to_relocate=True, preferred_cities=["hyderabad", "bengaluru"])
    result = market_demand(CAREER, student)
    assert (result.best_city, result.market_demand) == ("bengaluru", pytest.approx(0.865))


def test_relocating_without_preferences_uses_all_cities() -> None:
    student = school_student(willing_to_relocate=True)
    assert reachable_cities(student) == list(config.CITIES)
    assert market_demand(CAREER, student).best_city == "bengaluru"


def test_tied_cities_keep_the_student_order() -> None:
    tied = career([pathway("a"), pathway("b")], fields={"city_demand": DEMAND | {"pune": 0.85}})
    student = school_student(willing_to_relocate=True, preferred_cities=["pune", "hyderabad"])
    assert market_demand(tied, student).best_city == "pune"
