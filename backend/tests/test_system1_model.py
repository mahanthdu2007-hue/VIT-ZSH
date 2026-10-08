"""§7.3 System 1 on the real zero-shot model with the three §14 persona texts. Run with: pytest -q -m slow"""

import pytest

from app.engine import config
from app.engine.loader import get_dataset
from app.engine.system1 import ZeroShotNLIBackend, run_decisions
from app.models.schemas import TypedDecision
from app.settings import get_settings

# persona → (domain choice, None = abstains; domains expected in the top 2;
#            concerns expected above the §7.6 0.5 threshold)
EXPECTED: dict[str, tuple[str | None, set[str], set[str]]] = {
    "ananya": ("Technology", {"Technology"}, {"financial burden", "job security", "distance from home"}),
    "rahul": (None, {"Finance & Maths", "Technology"}, {"financial burden", "job security"}),
    "meera": ("Arts & Design", {"Arts & Design"}, {"job security"}),
}


def top_labels(decision: TypedDecision, count: int) -> set[str]:
    return set(sorted(decision.probabilities, key=lambda k: decision.probabilities[k], reverse=True)[:count])


@pytest.mark.slow
def test_real_model_on_persona_texts() -> None:
    backend = ZeroShotNLIBackend(get_settings().system1_model)
    for profile in get_dataset().demo_profiles:
        domain, concerns = run_decisions(backend, profile.student, profile.parent)
        expected_choice, expected_domains, expected_concerns = EXPECTED[profile.id]
        for decision in (domain, concerns):
            assert decision.backend == backend.name
            assert all(0.0 <= p <= 1.0 for p in decision.probabilities.values())
        assert domain.question_id == config.DECISION_STUDENT_DOMAIN
        assert domain.choice == expected_choice, profile.id
        assert expected_domains <= top_labels(domain, 2), profile.id
        strong = {label for label, p in concerns.probabilities.items() if p > config.PARENT_CONCERN_THRESHOLD}
        assert expected_concerns <= strong, profile.id
