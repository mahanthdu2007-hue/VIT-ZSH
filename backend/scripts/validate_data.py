"""Validate every data file: schema, value ranges, cross-references and §5 counts.

Usage: python scripts/validate_data.py [--data-dir PATH]
Exits with code 1 if any error is found. Warnings do not fail the check.
"""

import argparse
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
from app.models.schemas import (  # noqa: E402
    Career,
    City,
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
        bands = career.salary_inr_lpa
        mids = [sum(r) / 2 for r in (bands.entry, bands.mid, bands.senior)]
        if not mids[0] <= mids[1] <= mids[2]:
            report.errors.append(f"{where}: salary midpoints must rise entry ≤ mid ≤ senior")
        if not any(p.entry == "graduate" for p in career.pathways):
            report.warnings.append(f"{where}: no graduate (lateral) pathway")

    total = len(careers)
    if total == 0:
        report.warnings.append("no careers yet (expected while careers are not written)")
        report.row("careers (total)", 0, f"{config.CAREERS_TOTAL_MIN}–{config.CAREERS_TOTAL_MAX}", WARN)
    else:
        in_range = config.CAREERS_TOTAL_MIN <= total <= config.CAREERS_TOTAL_MAX
        if not in_range:
            report.errors.append(
                f"careers: {total} total, expected {config.CAREERS_TOTAL_MIN}–{config.CAREERS_TOTAL_MAX}"
            )
        report.row(
            "careers (total)", total,
            f"{config.CAREERS_TOTAL_MIN}–{config.CAREERS_TOTAL_MAX}", OK if in_range else FAIL,
        )
    by_domain = Counter(c.domain for c in careers)
    for domain, minimum in config.DOMAIN_MIN_CAREERS.items():
        count = by_domain[domain]
        if total == 0:
            status = WARN
        elif count < minimum:
            status = FAIL
            report.errors.append(f"careers: {domain} has {count}, minimum is {minimum}")
        else:
            status = OK
        report.row(f"  {domain}", count, f"≥ {minimum}", status)


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
    label: str,
    questions: QuestionSet | None,
    track: str,
    skill_names: set[str],
    careers: list[Career],
) -> None:
    if questions is None:
        report.row(label, "-", "valid file", FAIL)
        return
    if questions.track != track:
        report.errors.append(f"{label}: track is '{questions.track}', expected '{track}'")
    status = OK
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
                report.warnings.append(f"{label}: not among the 20 most common career skills {not_common}")
                status = WARN if status == OK else status
    sizes = f"{len(questions.aptitude)}/{len(questions.riasec)}/{len(questions.workstyle)}/{len(questions.free_text)}"
    expected = "12/18/4/2"
    if questions.skills is not None:
        sizes += f" + {len(questions.skills)} skills"
        expected += " + 20 skills"
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
    school = _load(report, data_dir / "questions_school.json", QuestionSet)
    college = _load(report, data_dir / "questions_college.json", QuestionSet)

    skill_names = {s.name for s in skills}
    _check_careers(report, careers, {e.id for e in exams}, skill_names)
    _check_reference_data(report, exams, scholarships, cities, skills)
    _check_questions(report, "questions_school", school, "school", skill_names, careers)
    _check_questions(report, "questions_college", college, "college", skill_names, careers)
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
