"""§8 Skill gap, roadmap and timeline."""

import math
from statistics import mean

from app.engine import config
from app.models.schemas import (
    Career,
    CollegeStudentInput,
    Pathway,
    RoadmapStep,
    SchoolStudentInput,
    SkillGap,
    SkillPlan,
    SkillVocabularyEntry,
    StudentInput,
    StudentVector,
    TimelineYear,
)


def current_level(
    skill: str, student: StudentInput, vector: StudentVector, vocabulary: dict[str, SkillVocabularyEntry]
) -> float:
    """§8 college: self-rating/100; school (or an unrated college skill): linked aptitude, else 0.2."""
    if isinstance(student, CollegeStudentInput) and skill in student.self_rated_skills:
        return student.self_rated_skills[skill] / config.SKILL_RATING_SCALE
    entry = vocabulary.get(skill)
    if entry is not None and entry.aptitude is not None:
        return vector.values[entry.aptitude]
    return config.SCHOOL_SKILL_BASELINE


def skill_gaps(
    career: Career, student: StudentInput, vector: StudentVector, vocabulary: dict[str, SkillVocabularyEntry]
) -> list[SkillGap]:
    """§8 gap = importance × max(0, level_required − current), sorted largest first."""
    gaps = []
    for skill in career.skills:
        current = current_level(skill.name, student, vector, vocabulary)
        gaps.append(SkillGap(
            skill=skill.name, importance=skill.importance, level_required=skill.level_required,
            current=current, gap=skill.importance * max(0.0, skill.level_required - current),
        ))
    return sorted(gaps, key=lambda g: -g.gap)


def roadmap(pathway: Pathway, gaps: list[SkillGap]) -> list[RoadmapStep]:
    """§8 pathway steps interleaved with gap-ordered learning steps."""
    learning = [
        RoadmapStep(kind="learning", skill=g.skill,
                    text=f"Build {g.skill} from {g.current:.0%} to {g.level_required:.0%}")
        for g in gaps if g.gap > 0
    ]
    steps: list[RoadmapStep] = []
    for i, text in enumerate(pathway.steps):
        steps.append(RoadmapStep(kind="pathway", text=text))
        if i < len(learning):
            steps.append(learning[i])
    steps += learning[len(pathway.steps):]
    return steps


def years_until_start(pathway: Pathway, student: StudentInput) -> int:
    """§8 whole years from now until the pathway's main programme begins."""
    if isinstance(student, SchoolStudentInput):
        final = config.SCHOOL_CLASS_10 if pathway.entry == "after_class_10" else config.SCHOOL_FINAL_CLASS
        return max(0, final - student.current_class) + 1
    return max(0, config.COLLEGE_UG_YEARS - student.year) + 1


def timeline(
    steps: list[RoadmapStep], pathway: Pathway, student: StudentInput, current_year: int
) -> list[TimelineYear]:
    """§8 roadmap steps placed on calendar years from the current year to the end of the pathway.

    Pathway steps are spread evenly; each learning step shares the year of the step before it.
    """
    end_year = current_year + years_until_start(pathway, student) + math.ceil(pathway.duration_years)
    n_pathway = sum(s.kind == "pathway" for s in steps)
    span = end_year - current_year
    years: dict[int, list[str]] = {}
    year, index = current_year, 0
    for step in steps:
        if step.kind == "pathway":
            fraction = index / (n_pathway - 1) if n_pathway > 1 else 0.0
            year = current_year + math.floor(fraction * span + 0.5)
            index += 1
        years.setdefault(year, []).append(step.text)
    return [TimelineYear(year=y, steps=s) for y, s in sorted(years.items())]


def skill_plan(
    career: Career,
    pathway: Pathway,
    student: StudentInput,
    vector: StudentVector,
    vocabulary: dict[str, SkillVocabularyEntry],
    current_year: int,
) -> SkillPlan:
    gaps = skill_gaps(career, student, vector, vocabulary)
    steps = roadmap(pathway, gaps)
    return SkillPlan(
        career_id=career.id,
        gaps=gaps,
        mean_gap=mean(g.gap for g in gaps),
        roadmap=steps,
        timeline=timeline(steps, pathway, student, current_year),
    )
