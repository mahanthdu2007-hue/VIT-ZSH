"""Deterministic text formatting shared by What-If reasons (§11) and template explanations (§12)."""

from app.engine import config


def format_inr(amount: int) -> str:
    """Indian digit grouping: 500000 → ₹5,00,000."""
    digits = str(abs(amount))
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    sign = "-" if amount < 0 else ""
    return f"{sign}₹{','.join([*groups, tail])}"


def points(component: str, value: float) -> str:
    """Points earned for a component, e.g. "26.4 of 30"."""
    return f"{value:.1f} of {config.SCORE_POINTS[component]:.0f}"
