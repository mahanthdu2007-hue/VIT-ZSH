"""Download and load every model once, so the demo works offline afterwards (§12).

Models: the System 1 zero-shot model (SYSTEM1_MODEL), its light fallback, and the System 2
embedding model. Then runs the System 1 decisions on the three demo personas with timings.
Usage: python scripts/warmup.py
"""

import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.engine import config  # noqa: E402
from app.engine.loader import get_dataset  # noqa: E402
from app.engine.system1 import ZeroShotNLIBackend, decision_inputs  # noqa: E402
from app.settings import get_settings  # noqa: E402

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # §3 System 2 embeddings


def timed_load(label: str, load: object) -> bool:
    start = time.perf_counter()
    try:
        load()  # type: ignore[operator]
    except Exception as exc:
        print(f"FAILED  {label}: {type(exc).__name__}: {exc}")
        return False
    print(f"ok      {label} ({time.perf_counter() - start:.1f} s)")
    return True


def show_persona_decisions(backend: ZeroShotNLIBackend) -> None:
    print(f"\nSystem 1 decisions with {backend.model_name}")
    for profile in get_dataset().demo_profiles:
        for question_id, text, options in decision_inputs(profile.student, profile.parent):
            start = time.perf_counter()
            decision = backend.decide(text, question_id, list(options), config.HYPOTHESIS_TEMPLATES[question_id])
            elapsed_ms = (time.perf_counter() - start) * 1000
            top = sorted(decision.probabilities.items(), key=lambda kv: kv[1], reverse=True)[:3]
            shown = ", ".join(f"{label} {p:.2f}" for label, p in top)
            outcome = "abstained" if decision.abstained else f"choice: {decision.choice}"
            print(f"  {profile.name:<7} {question_id:<24} {outcome:<25} conf {decision.confidence:.2f} "
                  f"margin {decision.margin:.2f} {elapsed_ms:5.0f} ms | {shown}")


def main() -> int:
    settings = get_settings()
    primary = ZeroShotNLIBackend(settings.system1_model)
    results = [
        timed_load(f"System 1 model {settings.system1_model}", primary.load),
        timed_load(f"System 1 fallback {config.SYSTEM1_FALLBACK_MODEL}",
                   ZeroShotNLIBackend(config.SYSTEM1_FALLBACK_MODEL).load),
    ]

    def load_embeddings() -> None:
        from sentence_transformers import SentenceTransformer

        SentenceTransformer(EMBEDDING_MODEL, device="cpu").encode(["warm-up"])

    results.append(timed_load(f"System 2 embeddings {EMBEDDING_MODEL}", load_embeddings))
    if results[0]:
        show_persona_decisions(primary)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
