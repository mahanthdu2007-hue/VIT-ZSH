"""§10 Return on investment: break-even years."""

from app.engine import config
from app.engine.scoring import entry_mid_inr
from app.models.schemas import Career, Roi


def roi(career: Career, effective_cost: int) -> Roi:
    """§10 break_even_years = effective_cost / (0.25 × entry_mid_inr); the 25% is shown in the UI."""
    entry_mid = entry_mid_inr(career)
    return Roi(
        career_id=career.id,
        effective_cost=effective_cost,
        entry_mid_inr=entry_mid,
        salary_share=config.ROI_SALARY_SHARE,
        break_even_years=effective_cost / (config.ROI_SALARY_SHARE * entry_mid),
    )
