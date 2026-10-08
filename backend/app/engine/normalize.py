"""§7.1–§7.2 Ingest and Vectorize & Normalize: student vector, preference values, completeness."""

from statistics import mean

from app.engine import config
from app.models.schemas import (
    Completeness,
    ParentInput,
    ParentPreferences,
    QuestionSet,
    SchoolStudentInput,
    StudentInput,
    StudentPreferences,
    StudentVector,
    Stream,
    Track,
)


def question_set_id(track: Track, stream: Stream | None) -> str:
    """§5 the short question set for a student's path: college, Class 9–10 (no stream yet) or Class 11–12 by stream."""
    if track == "college":
        return config.QUESTION_SET_COLLEGE
    return config.QUESTION_SET_CLASS_9_10 if stream is None else config.QUESTION_SET_BY_STREAM[stream]


def student_question_set_id(student: StudentInput) -> str:
    return question_set_id(student.track, student.stream if isinstance(student, SchoolStudentInput) else None)


def likert_value(answer: int) -> float:
    """§7.2 Likert answer 1–5 → (x − 1)/4."""
    return (answer - config.LIKERT_MIN) / config.LIKERT_RANGE


def _likert_mean(answers: dict[str, int], item_ids: list[str]) -> float | None:
    given = [likert_value(answers[i]) for i in item_ids if i in answers]
    return mean(given) if given else None


def student_vector(student: StudentInput, questions: QuestionSet) -> StudentVector:
    """§7.2 student vector S over the 11 dimensions, all in [0, 1]."""
    values: dict[str, float] = {}
    correct: dict[str, int] = {}
    defaulted: list[str] = []

    for dim in config.APTITUDE_DIMENSIONS:
        items = [i for i in questions.aptitude if i.dimension == dim]
        correct[dim] = sum(student.aptitude_answers.get(i.id) == i.answer for i in items)
        values[dim] = correct[dim] / config.APTITUDE_ITEMS_PER_DIMENSION

    for dim in config.RIASEC_DIMENSIONS:
        ids = [i.id for i in questions.riasec if i.dimension == dim]
        score = _likert_mean(student.riasec_answers, ids)
        if score is None:
            defaulted.append(dim)
        values[dim] = config.LIKERT_NEUTRAL if score is None else score

    creative_ids = [i.id for i in questions.workstyle if i.dimension == "creative"]
    creative_item = _likert_mean(student.workstyle_answers, creative_ids)
    if creative_item is None:
        defaulted.append("creative")
        creative_item = config.LIKERT_NEUTRAL
    values["creative"] = mean([creative_item, values["A"]])

    ordered = {dim: values[dim] for dim in config.STUDENT_DIMENSIONS}
    return StudentVector(values=ordered, aptitude_correct=correct, defaulted=defaulted)


def student_preferences(student: StudentInput, questions: QuestionSet) -> StudentPreferences:
    stability_ids = [i.id for i in questions.workstyle if i.dimension == "stability_vs_excitement"]
    stability = _likert_mean(student.workstyle_answers, stability_ids)
    marks = None if student.marks_percent is None else student.marks_percent / config.MARKS_SCALE
    return StudentPreferences(
        risk_tolerance=config.LEVEL_VALUES[student.risk_tolerance],
        relocation=config.BOOL_VALUES[student.willing_to_relocate],
        higher_studies=config.BOOL_VALUES[student.wants_higher_studies],
        stability=config.LIKERT_NEUTRAL if stability is None else stability,
        marks=marks,
    )


def parent_preferences(parent: ParentInput) -> ParentPreferences:
    return ParentPreferences(
        risk_appetite=config.LEVEL_VALUES[parent.risk_appetite],
        location=config.LOCATION_PREFERENCE_VALUE[parent.location_preference],
        higher_studies=config.BOOL_VALUES[parent.supports_higher_studies],
        priority_stability=config.PRIORITY_STABILITY_VALUE[parent.top_priority],
    )


def free_text_answered(text: str) -> bool:
    """§6 free text counts as answered at ≥ 15 words."""
    return len(text.split()) >= config.FREE_TEXT_MIN_WORDS


def completeness(student: StudentInput, parent: ParentInput, questions: QuestionSet) -> Completeness:
    """§6 profile completeness = answered fields / total fields, with the missing field names."""
    fields: list[tuple[str, bool]] = []
    for prefix, items, answers in (
        ("aptitude", questions.aptitude, student.aptitude_answers),
        ("riasec", questions.riasec, student.riasec_answers),
        ("workstyle", questions.workstyle, student.workstyle_answers),
    ):
        fields += [(f"{prefix}:{item.id}", item.id in answers) for item in items]

    if isinstance(student, SchoolStudentInput):
        fields.append(("current_class", True))
        if student.current_class >= config.STREAM_FROM_CLASS:
            fields.append(("stream", student.stream is not None))
    else:
        fields += [("degree", True), ("year", True)]
        fields += [(f"skill:{s}", s in student.self_rated_skills) for s in questions.skills or []]

    fields += [
        ("marks_percent", student.marks_percent is not None),
        ("favourite_subjects", bool(student.favourite_subjects)),
        ("home_city", True),
        ("preferred_cities", bool(student.preferred_cities)),
        ("willing_to_relocate", True),
        ("wants_higher_studies", True),
        ("risk_tolerance", True),
        ("dream_career_id", student.dream_career_id is not None),
        ("free_text_1", free_text_answered(student.free_text_1)),
        ("free_text_2", free_text_answered(student.free_text_2)),
        ("parent.annual_income_inr", True),
        ("parent.education_budget_inr", True),
        ("parent.loan_willingness", True),
        ("parent.risk_appetite", True),
        ("parent.preferred_domains", bool(parent.preferred_domains)),
        ("parent.location_preference", True),
        ("parent.supports_higher_studies", True),
        ("parent.top_priority", True),
        ("parent.free_text", free_text_answered(parent.free_text)),
    ]
    answered = sum(ok for _, ok in fields)
    return Completeness(
        score=answered / len(fields),
        answered=answered,
        total=len(fields),
        missing=[name for name, ok in fields if not ok],
    )
