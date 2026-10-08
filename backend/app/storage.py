"""Saved assessments in SQLite through SQLAlchemy (Postgres-ready via DATABASE_URL, §3).

Each row keeps the inputs with the System 1 decisions, and the full result, in separate columns:
What-If reads only the small inputs column and re-runs the pipeline without System 1 (§11).
LLM explanations (§12) are written later by a background task, into their own table.
"""

from datetime import datetime
from functools import lru_cache

from sqlalchemy import DateTime, Engine, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.models.schemas import AssessmentInputs, AssessmentResult, Explanations
from app.settings import get_settings


class Base(DeclarativeBase):
    pass


class AssessmentRow(Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    inputs_json: Mapped[str] = mapped_column(Text)
    result_json: Mapped[str] = mapped_column(Text)


class ExplanationRow(Base):
    __tablename__ = "explanations"

    assessment_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    explanations_json: Mapped[str] = mapped_column(Text)


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args)
    Base.metadata.create_all(engine)
    return engine


def save_assessment(inputs: AssessmentInputs, result: AssessmentResult, created_at: datetime) -> None:
    with Session(get_engine()) as session:
        session.add(AssessmentRow(id=result.id, created_at=created_at, inputs_json=inputs.model_dump_json(),
                                  result_json=result.model_dump_json()))
        session.commit()


def _column(column: Mapped[str], assessment_id: str) -> str | None:
    """Read one JSON column only, so What-If does not load the large result."""
    with Session(get_engine()) as session:
        return session.scalar(select(column).where(AssessmentRow.id == assessment_id))


def load_inputs(assessment_id: str) -> AssessmentInputs | None:
    raw = _column(AssessmentRow.inputs_json, assessment_id)
    return None if raw is None else AssessmentInputs.model_validate_json(raw)


def load_result(assessment_id: str) -> AssessmentResult | None:
    raw = _column(AssessmentRow.result_json, assessment_id)
    return None if raw is None else AssessmentResult.model_validate_json(raw)


def save_explanations(assessment_id: str, explanations: Explanations) -> None:
    with Session(get_engine()) as session:
        session.merge(ExplanationRow(assessment_id=assessment_id, explanations_json=explanations.model_dump_json()))
        session.commit()


def load_explanations(assessment_id: str) -> Explanations | None:
    with Session(get_engine()) as session:
        raw = session.scalar(select(ExplanationRow.explanations_json)
                             .where(ExplanationRow.assessment_id == assessment_id))
    return None if raw is None else Explanations.model_validate_json(raw)
