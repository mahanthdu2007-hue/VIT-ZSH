"""Loads every data file once, validated through the Pydantic models, and caches the result."""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.models.schemas import (
    Career,
    City,
    Dataset,
    Exam,
    QuestionSet,
    Scholarship,
    SkillVocabularyEntry,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CAREERS_SUBDIR = "careers"


class DataFileError(Exception):
    """A data file is missing, is not valid JSON, or does not match its model."""


def load_file(path: Path, model: Any) -> Any:
    """Parse one JSON file with a type such as list[Exam] or QuestionSet."""
    try:
        return TypeAdapter(model).validate_json(path.read_bytes())
    except FileNotFoundError as exc:
        raise DataFileError(f"{path.name}: file not found") from exc
    except ValidationError as exc:
        raise DataFileError(f"{path.name}: {exc}") from exc


def career_files(data_dir: Path) -> list[Path]:
    return sorted((data_dir / CAREERS_SUBDIR).glob("*.json"))


def load_careers(data_dir: Path) -> list[Career]:
    careers: list[Career] = []
    for path in career_files(data_dir):
        careers.extend(load_file(path, list[Career]))
    return careers


def load_dataset(data_dir: Path = DATA_DIR) -> Dataset:
    return Dataset(
        careers=load_careers(data_dir),
        exams=load_file(data_dir / "exams.json", list[Exam]),
        scholarships=load_file(data_dir / "scholarships.json", list[Scholarship]),
        cities=load_file(data_dir / "cities.json", list[City]),
        skills=load_file(data_dir / "skills_vocabulary.json", list[SkillVocabularyEntry]),
        questions_school=load_file(data_dir / "questions_school.json", QuestionSet),
        questions_college=load_file(data_dir / "questions_college.json", QuestionSet),
    )


@lru_cache(maxsize=1)
def get_dataset() -> Dataset:
    """The cached dataset used by the engine and API."""
    return load_dataset()
