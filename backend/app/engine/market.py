"""§7.7 Market Intelligence: Industry Hiring Index (MD) and best city."""

from app.engine import config
from app.models.schemas import Career, MarketDemand, StudentInput


def reachable_cities(student: StudentInput) -> list[str]:
    """§7.7 home city if not relocating; else preferred cities, or all cities if none chosen."""
    if not student.willing_to_relocate:
        return [student.home_city]
    return list(student.preferred_cities) or list(config.CITIES)


def market_demand(career: Career, student: StudentInput) -> MarketDemand:
    """§7.7 MD = 0.5·local_demand + 0.3·job_velocity + 0.2·(1 − disruption_index)."""
    cities = reachable_cities(student)
    best_city = max(cities, key=lambda c: (career.city_demand[c], -cities.index(c)))  # type: ignore[index]
    local = career.city_demand[best_city]  # type: ignore[index]
    value = (config.MD_WEIGHT_LOCAL_DEMAND * local
             + config.MD_WEIGHT_JOB_VELOCITY * career.job_velocity
             + config.MD_WEIGHT_STABILITY * (1 - career.disruption_index))
    return MarketDemand(career_id=career.id, local_demand=local, best_city=best_city, market_demand=value)
