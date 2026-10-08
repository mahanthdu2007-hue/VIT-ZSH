"""§12 DEMO_MODE disk cache: full results for the demo profiles, so the live demo needs no model.

Only requests that match a demo profile exactly are cached. The key includes a hash of every data
file, so changed data never serves an old result. Delete backend/cache/ after changing engine code.
"""

import hashlib
from functools import lru_cache
from pathlib import Path

from app.engine.loader import DATA_DIR
from app.models.schemas import AssessRequest, Dataset, DemoCacheEntry

CACHE_DIR = Path(__file__).resolve().parents[1] / "cache"


@lru_cache(maxsize=1)
def data_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in sorted(DATA_DIR.rglob("*.json")):
        digest.update(path.relative_to(DATA_DIR).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def demo_profile_id(request: AssessRequest, data: Dataset) -> str | None:
    """The demo profile this request is identical to, if any."""
    for profile in data.demo_profiles:
        if profile.student == request.student and profile.parent == request.parent:
            return profile.id
    return None


def cache_path(profile_id: str, request: AssessRequest) -> Path:
    key = hashlib.sha256((request.model_dump_json() + data_fingerprint()).encode()).hexdigest()[:16]
    return CACHE_DIR / f"demo_{profile_id}_{key}.json"


def load(profile_id: str, request: AssessRequest) -> DemoCacheEntry | None:
    path = cache_path(profile_id, request)
    if not path.exists():
        return None
    return DemoCacheEntry.model_validate_json(path.read_bytes())


def save(profile_id: str, request: AssessRequest, entry: DemoCacheEntry) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path(profile_id, request).write_text(entry.model_dump_json(), encoding="utf-8")
