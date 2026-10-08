"""Validate every data file: schema, value ranges, cross-references and §5 counts.

Usage: python scripts/validate_data.py [--data-dir PATH]
Exits with code 1 if any error is found. Warnings do not fail the check.
"""

import argparse
import math
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.engine import config  # noqa: E402
from app.engine.loader import DATA_DIR, DataFileError, career_files, load_file  # noqa: E402
from app.engine.normalize import student_question_set_id  # noqa: E402
from app.models.schemas import (  # noqa: E402
    Career,
    City,
    CollegeStudentInput,
    DemoProfile,
    Exam,
    QuestionSet,
    Scholarship,
    SkillVocabularyEntry,
)

OK, WARN, FAIL = "ok", "warning", "FAIL"


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rows: list[tuple[str, str, str, str]] = field(default_factory=list)

    def row(self, item: str, count: object, expected: str, status: str) -> None:
        self.rows.append((item, str(count), expected, status))


def _load(report: Report, path: Path, model: Any) -> Any:
    try:
        return load_file(path, model)
    except DataFileError as exc:
        report.errors.append(str(exc))
        return None


def _check_unique(report: Report, label: str, ids: Iterable[str]) -> None:
    duplicates = sorted(i for i, n in Counter(ids).items() if n > 1)
    if duplicates:
        report.errors.append(f"{label}: duplicate ids {duplicates}")


def _centred_cosine(a: list[float], b: list[float]) -> float:
    """§7.5 matching measure: cosine of (vector − 0.5)."""
    ca = [x - config.MATCH_CENTRE for x in a]
    cb = [x - config.MATCH_CENTRE for x in b]
    norm = math.sqrt(sum(x * x for x in ca)) * math.sqrt(sum(x * x for x in cb))
    return sum(x * y for x, y in zip(ca, cb)) / norm if norm else 1.0


def _check_requirement_vectors(report: Report, careers: list[Career]) -> None:
    vectors = [
        [c.requirement_vector.model_dump()[d] for d in config.STUDENT_DIMENSIONS] for c in careers
    ]
    closest = 0.0
    for i in range(len(careers)):
        for j in range(i + 1, len(careers)):
            similarity = _centred_cosine(vectors[i], vectors[j])
            closest = max(closest, similarity)
            if similarity > config.REQUIREMENT_COSINE_MAX:
                report.errors.append(
                    f"careers {careers[i].id} and {careers[j].id}: near-identical requirement vectors "
                    f"(centred cosine {similarity:.3f})"
                )
    if len(careers) > 1:
        status = OK if closest <= config.REQUIREMENT_COSINE_MAX else FAIL
        report.row("  closest vector pair", f"{closest:.2f}", f"≤ {config.REQUIREMENT_COSINE_MAX}", status)


def _check_careers(
    report: Report, careers: list[Career], exam_ids: set[str], skill_names: set[str]
) -> None:
    career_ids = {c.id for c in careers}
    _check_unique(report, "careers", (c.id for c in careers))
    for career in careers:
        where = f"career {career.id}"
        for adjacent in career.adjacent_careers:
            if adjacent == career.id:
                report.errors.append(f"{where}: lists itself as an adjacent career")
            elif adjacent not in career_ids:
                report.errors.append(f"{where}: unknown adjacent career '{adjacent}'")
        for skill in career.skills:
            if skill.name not in skill_names:
                report.errors.append(f"{where}: skill '{skill.name}' is not in skills_vocabulary.json")
        for pathway in career.pathways:
            for exam in pathway.entrance_exams:
                if exam not in exam_ids:
                    report.errors.append(f"{where}, pathway {pathway.id}: unknown exam '{exam}'")
        bands = (career.salary_inr_lpa.entry, career.salary_inr_lpa.mid, career.salary_inr_lpa.senior)
        mids = [sum(r) / 2 for r in bands]
        lows_rise = bands[0][0] <= bands[1][0] <= bands[2][0]
        highs_rise = bands[0][1] <= bands[1][1] <= bands[2][1]
        if not (mids[0] < mids[1] < mids[2] and lows_rise and highs_rise):
            report.errors.append(f"{where}: salaries must increase entry → mid → senior")
        if not any(p.entry == "graduate" for p in career.pathways):
            report.warnings.append(f"{where}: no graduate (lateral) pathway")

    names = Counter(c.name.casefold() for c in careers)
    for name in sorted(n for n, k in names.items() if k > 1):
        report.errors.append(f"careers: duplicate career name '{name}'")

    # Careers are written in batches: a domain with no careers yet is a warning, but any
    # domain that has careers must meet its minimum, and the total is enforced once all exist.
    total = len(careers)
    by_domain = Counter(c.domain for c in careers)
    unwritten = [d for d in config.DOMAIN_MIN_CAREERS if by_domain[d] == 0]
    expected_total = f"{config.CAREERS_TOTAL_MIN}–{config.CAREERS_TOTAL_MAX}"
    if unwritten:
        report.warnings.append(f"no careers yet for {unwritten} (expected until every batch is written)")
        report.row("careers (total)", total, expected_total, WARN)
    else:
        in_range = config.CAREERS_TOTAL_MIN <= total <= config.CAREERS_TOTAL_MAX
        if not in_range:
            report.errors.append(f"careers: {total} total, expected {expected_total}")
        report.row("careers (total)", total, expected_total, OK if in_range else FAIL)
    for domain, minimum in config.DOMAIN_MIN_CAREERS.items():
        count = by_domain[domain]
        if count == 0:
            status = WARN
        elif count < minimum:
            status = FAIL
            report.errors.append(f"careers: {domain} has {count}, minimum is {minimum}")
        else:
            status = OK
        report.row(f"  {domain}", count, f"≥ {minimum}", status)
    _check_requirement_vectors(report, careers)


def _word_count(text: str) -> int:
    return len(text.split())


def _check_demo_profiles(
    report: Report,
    profiles: list[DemoProfile],
    questions: dict[str, QuestionSet | None],
    career_ids: set[str],
) -> None:
    _check_unique(report, "demo profiles", (p.id for p in profiles))
    for profile in profiles:
        where = f"demo profile {profile.id}"
        student = profile.student
        question_set = questions[student_question_set_id(student)]
        if question_set is not None:
            answers = {
                "aptitude": (student.aptitude_answers, question_set.aptitude),
                "riasec": (student.riasec_answers, question_set.riasec),
                "workstyle": (student.workstyle_answers, question_set.workstyle),
            }
            for section, (given, items) in answers.items():
                expected = {i.id for i in items}
                if set(given) != expected:
                    missing, extra = sorted(expected - set(given)), sorted(set(given) - expected)
                    report.errors.append(f"{where}: {section} answers missing {missing}, unknown {extra}")
            for item in question_set.aptitude:
                choice = student.aptitude_answers.get(item.id)
                if choice is not None and choice >= len(item.options):
                    report.errors.append(f"{where}: {item.id} answer {choice} is out of range")
            if isinstance(student, CollegeStudentInput) and set(student.self_rated_skills) != set(
                question_set.skills or []
            ):
                report.errors.append(f"{where}: self_rated_skills must rate exactly the college skills list")
        if student.dream_career_id is not None and student.dream_career_id not in career_ids:
            report.errors.append(f"{where}: unknown dream career '{student.dream_career_id}'")
        unfilled = [
            name for name, value in (
                ("marks_percent", student.marks_percent),
                ("favourite_subjects", student.favourite_subjects),
                ("preferred_cities", student.preferred_cities),
                ("dream_career_id", student.dream_career_id),
                ("parent.preferred_domains", profile.parent.preferred_domains),
            ) if not value
        ]
        if unfilled:
            report.errors.append(f"{where}: demo profiles must fill every field, missing {unfilled}")
        texts = {
            "free_text_1": student.free_text_1,
            "free_text_2": student.free_text_2,
            "parent.free_text": profile.parent.free_text,
        }
        for name, text in texts.items():
            words = _word_count(text)
            if not config.DEMO_FREE_TEXT_MIN_WORDS <= words <= config.DEMO_FREE_TEXT_MAX_WORDS:
                report.errors.append(
                    f"{where}: {name} has {words} words, expected "
                    f"{config.DEMO_FREE_TEXT_MIN_WORDS}–{config.DEMO_FREE_TEXT_MAX_WORDS}"
                )
    count_ok = len(profiles) == config.DEMO_PROFILE_COUNT
    if not count_ok:
        report.errors.append(f"demo profiles: {len(profiles)}, expected {config.DEMO_PROFILE_COUNT}")
    report.row("demo profiles", len(profiles), str(config.DEMO_PROFILE_COUNT), OK if count_ok else FAIL)


def _check_reference_data(
    report: Report,
    exams: list[Exam],
    scholarships: list[Scholarship],
    cities: list[City],
    skills: list[SkillVocabularyEntry],
) -> None:
    _check_unique(report, "exams", (e.id for e in exams))
    covered = {d for e in exams for d in e.domains}
    missing_domains = sorted(set(config.DOMAIN_MIN_CAREERS) - covered)
    missing_levels = sorted({"school", "ug", "pg"} - {e.level for e in exams})
    if missing_domains:
        report.errors.append(f"exams: no exam covers {missing_domains}")
    if missing_levels:
        report.errors.append(f"exams: no exam at level {missing_levels}")
    report.row("exams", len(exams), "all 7 domains, 3 levels",
               FAIL if missing_domains or missing_levels or not exams else OK)

    _check_unique(report, "scholarships", (s.id for s in scholarships))
    n = len(scholarships)
    in_range = config.SCHOLARSHIPS_MIN <= n <= config.SCHOLARSHIPS_MAX
    if not in_range:
        report.errors.append(
            f"scholarships: {n}, expected {config.SCHOLARSHIPS_MIN}–{config.SCHOLARSHIPS_MAX}"
        )
    open_count = sum(s.restricted_to is None for s in scholarships)
    report.row("scholarships", n, f"{config.SCHOLARSHIPS_MIN}–{config.SCHOLARSHIPS_MAX}",
               OK if in_range else FAIL)
    report.row("  open to everyone", open_count, "info", OK)

    city_ids = [c.id for c in cities]
    _check_unique(report, "cities", city_ids)
    exact = sorted(city_ids) == sorted(config.CITIES)
    if not exact:
        report.errors.append(f"cities: expected exactly {sorted(config.CITIES)}, got {sorted(city_ids)}")
    report.row("cities", len(cities), str(len(config.CITIES)), OK if exact else FAIL)

    _check_unique(report, "skills vocabulary", (s.name for s in skills))
    size_ok = config.SKILL_VOCABULARY_MIN <= len(skills) <= config.SKILL_VOCABULARY_MAX
    if not size_ok:
        report.warnings.append(f"skills vocabulary has {len(skills)} skills, expected about 60")
    report.row("skills vocabulary", len(skills),
               f"{config.SKILL_VOCABULARY_MIN}–{config.SKILL_VOCABULARY_MAX}", OK if size_ok else WARN)


def _check_questions(
    report: Report,
    set_id: str,
    questions: QuestionSet | None,
    skill_names: set[str],
    careers: list[Career],
) -> None:
    label = f"questions_{set_id}"
    if questions is None:
        report.row(label, "-", "valid file", FAIL)
        return
    status = OK
    if questions.id != set_id:
        report.errors.append(f"{label}: id is '{questions.id}', expected '{set_id}'")
        status = FAIL
    if questions.skills is not None:
        unknown = [s for s in questions.skills if s not in skill_names]
        if unknown:
            report.errors.append(f"{label}: skills not in vocabulary {unknown}")
            status = FAIL
        if careers:
            counts = Counter(s.name for c in careers for s in c.skills)
            cutoff = counts.most_common(config.COLLEGE_SKILL_LIST_SIZE)[-1][1]
            not_common = [s for s in questions.skills if counts[s] < cutoff]
            if not_common:
                report.warnings.append(
                    f"{label}: not among the {config.COLLEGE_SKILL_LIST_SIZE} most common career skills {not_common}"
                )
                status = WARN if status == OK else status
    sizes = f"{len(questions.aptitude)}/{len(questions.riasec)}/{len(questions.workstyle)}/{len(questions.free_text)}"
    expected = (f"{config.APTITUDE_ITEMS_TOTAL}/{config.RIASEC_ITEMS_PER_DIMENSION * len(config.RIASEC_DIMENSIONS)}"
                f"/{len(config.WORKSTYLE_DIMENSIONS)}/{len(config.FREE_TEXT_IDS)}")
    if questions.skills is not None:
        sizes += f" + {len(questions.skills)} skills"
        expected += f" + {config.COLLEGE_SKILL_LIST_SIZE} skills"
    report.row(label, sizes, expected, status)


def validate(data_dir: Path = DATA_DIR) -> Report:
    report = Report()
    careers: list[Career] = []
    for path in career_files(data_dir):
        careers.extend(_load(report, path, list[Career]) or [])
    exams: list[Exam] = _load(report, data_dir / "exams.json", list[Exam]) or []
    scholarships: list[Scholarship] = (
        _load(report, data_dir / "scholarships.json", list[Scholarship]) or []
    )
    cities: list[City] = _load(report, data_dir / "cities.json", list[City]) or []
    skills: list[SkillVocabularyEntry] = (
        _load(report, data_dir / "skills_vocabulary.json", list[SkillVocabularyEntry]) or []
    )
    question_sets: dict[str, QuestionSet | None] = {
        set_id: _load(report, data_dir / f"questions_{set_id}.json", QuestionSet) for set_id in config.QUESTION_SET_IDS
    }
    profiles: list[DemoProfile] = (
        _load(report, data_dir / "demo_profiles.json", list[DemoProfile]) or []
    )

    skill_names = {s.name for s in skills}
    _check_careers(report, careers, {e.id for e in exams}, skill_names)
    _check_reference_data(report, exams, scholarships, cities, skills)
    for set_id, question_set in question_sets.items():
        _check_questions(report, set_id, question_set, skill_names, careers)
    _check_demo_profiles(report, profiles, question_sets, {c.id for c in careers})
    return report


def print_report(report: Report) -> None:
    headers = ("Item", "Count", "Expected", "Status")
    widths = [max(len(r[i]) for r in (headers, *report.rows)) for i in range(4)]
    line = "  ".join("-" * w for w in widths)
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print(line)
    for row in report.rows:
        print("  ".join(cell.ljust(w) for cell, w in zip(row, widths)))
    print(line)
    for warning in report.warnings:
        print(f"WARNING: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")
    print(f"\n{len(report.errors)} error(s), {len(report.warnings)} warning(s)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    report = validate(args.data_dir)
    print_report(report)
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
