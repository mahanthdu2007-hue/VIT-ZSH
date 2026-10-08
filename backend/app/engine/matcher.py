"""§7.5 Career Matcher: centred cosine and Student Fit."""

import math
from collections.abc import Sequence

from app.engine import config
from app.models.schemas import Career, StudentFit, StudentVector


def centred_cosine(student: Sequence[float], requirement: Sequence[float]) -> float:
    """§7.5 cos(S − 0.5, R − 0.5) mapped to [0, 1] via (cos + 1)/2.

    If either centred vector is all zeros (every value 0.5) the angle is undefined; that is
    treated as cos = 0, i.e. a neutral 0.5.
    """
    s = [x - config.MATCH_CENTRE for x in student]
    r = [x - config.MATCH_CENTRE for x in requirement]
    norm = math.sqrt(sum(x * x for x in s)) * math.sqrt(sum(x * x for x in r))
    cos = sum(a * b for a, b in zip(s, r)) / norm if norm else 0.0
    return (cos + 1) / 2


def academic_alignment(marks: float | None, career: Career) -> float:
    """§7.5 marks weighted by how numerical/verbal the career is: 1 − w·(1 − marks).

    w = mean of the career's academic requirements, so marks matter more for academic careers.
    """
    m = config.MARKS_NEUTRAL if marks is None else marks
    requirements = career.requirement_vector.model_dump()
    weight = sum(requirements[d] for d in config.ACADEMIC_DIMENSIONS) / len(config.ACADEMIC_DIMENSIONS)
    return 1 - weight * (1 - m)


def student_fit(
    vector: StudentVector, career: Career, domain_affinity: dict[str, float], marks: float | None
) -> StudentFit:
    """§7.5 SF = 0.6·centred_cos + 0.25·domain_affinity[domain] + 0.15·academic_alignment."""
    requirements = career.requirement_vector.model_dump()
    cos = centred_cosine(
        [vector.values[d] for d in config.STUDENT_DIMENSIONS],
        [requirements[d] for d in config.STUDENT_DIMENSIONS],
    )
    affinity = domain_affinity.get(career.domain, 0.0)
    alignment = academic_alignment(marks, career)
    return StudentFit(
        career_id=career.id,
        centred_cosine=cos,
        domain_affinity=affinity,
        academic_alignment=alignment,
        student_fit=(config.SF_WEIGHT_COSINE * cos
                     + config.SF_WEIGHT_DOMAIN_AFFINITY * affinity
                     + config.SF_WEIGHT_ACADEMIC * alignment),
    )


def match_all(
    vector: StudentVector, careers: list[Career], domain_affinity: dict[str, float], marks: float | None
) -> list[StudentFit]:
    return [student_fit(vector, c, domain_affinity, marks) for c in careers]
