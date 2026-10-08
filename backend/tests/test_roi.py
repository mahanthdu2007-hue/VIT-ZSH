import pytest
from factories import career, pathway

from app.engine.roi import roi

TWO_PATHS = [pathway("a"), pathway("b")]


def salary_career(entry: list[float]):  # type: ignore[no-untyped-def]
    return career(TWO_PATHS, fields={"salary_inr_lpa": {"entry": entry, "mid": [20, 30], "senior": [40, 60]}})


@pytest.mark.parametrize(
    ("entry", "effective_cost", "years"),
    [
        ([6, 12], 350000, 350000 / (0.25 * 900000)),  # 1.556 years
        ([3, 5], 1000000, 10.0),                       # 10,00,000 / (0.25 × 4,00,000)
        ([4, 8], 0, 0.0),                              # free pathway
    ],
)
def test_break_even_years(entry: list[float], effective_cost: int, years: float) -> None:
    result = roi(salary_career(entry), effective_cost)
    assert result.break_even_years == pytest.approx(years)
    assert result.salary_share == 0.25
