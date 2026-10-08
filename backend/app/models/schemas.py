from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt, model_validator

from app.engine import config

# ---------------------------------------------------------------- shared types
Unit = Annotated[float, Field(ge=0.0, le=1.0)]
Domain = Literal[
    "Technology", "Engineering", "Science", "Health",
    "Arts & Design", "Finance & Maths", "Hyper-local",
]
CityId = Literal[
    "bengaluru", "mysuru", "chennai", "hyderabad", "pune", "delhi_ncr", "mumbai", "coimbatore",
]
Level = Literal["low", "medium", "high"]
Entry = Literal["after_class_10", "after_class_12", "graduate"]
InstitutionType = Literal["govt", "private", "online", "diploma"]
StudyLevel = Literal["school", "diploma", "ug", "pg"]
ExamLevel = Literal["school", "ug", "pg"]
Month = Literal[
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
AptitudeDimension = Literal["numerical", "logical", "verbal", "spatial"]
RiasecDimension = Literal["R", "I", "A", "S", "E", "C"]
WorkstyleDimension = Literal["creative", "stability_vs_excitement", "teamwork", "structure"]
FreeTextId = Literal["free_text_1", "free_text_2"]
Track = Literal["school", "college"]
Stream = Literal["PCM", "PCB", "PCMB", "Commerce", "Humanities"]
LikertAnswer = Annotated[int, Field(ge=config.LIKERT_MIN, le=config.LIKERT_MAX)]
SkillRating = Annotated[int, Field(ge=0, le=int(config.SKILL_RATING_SCALE))]
NonEmptyStr = Annotated[str, Field(min_length=1)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- §5 careers
class RequirementVector(StrictModel):
    numerical: Unit
    logical: Unit
    verbal: Unit
    spatial: Unit
    creative: Unit
    R: Unit
    I: Unit
    A: Unit
    S: Unit
    E: Unit
    C: Unit


class Skill(StrictModel):
    name: NonEmptyStr
    importance: Unit
    level_required: Unit


class CostRange(StrictModel):
    min: NonNegativeInt
    max: NonNegativeInt

    @model_validator(mode="after")
    def min_not_above_max(self) -> Self:
        if self.min > self.max:
            raise ValueError(f"cost min {self.min} is above max {self.max}")
        return self


class Pathway(StrictModel):
    id: NonEmptyStr
    label: NonEmptyStr
    entry: Entry
    steps: list[NonEmptyStr] = Field(min_length=1)
    duration_years: float = Field(gt=0)
    cost_inr: CostRange
    institution_type: InstitutionType
    entrance_exams: list[str]
    quality: Unit


SalaryRangeLpa = tuple[Annotated[float, Field(ge=0)], Annotated[float, Field(ge=0)]]


class SalaryBands(StrictModel):
    entry: SalaryRangeLpa
    mid: SalaryRangeLpa
    senior: SalaryRangeLpa

    @model_validator(mode="after")
    def ranges_ordered(self) -> Self:
        for band, (low, high) in (("entry", self.entry), ("mid", self.mid), ("senior", self.senior)):
            if low > high:
                raise ValueError(f"salary {band} range {low}–{high} is reversed")
        return self


class Career(StrictModel):
    id: NonEmptyStr
    name: NonEmptyStr
    domain: Domain
    steam: list[Literal["S", "T", "E", "A", "M"]] = Field(min_length=1)
    summary: NonEmptyStr
    requirement_vector: RequirementVector
    skills: list[Skill] = Field(min_length=1)
    pathways: list[Pathway] = Field(
        min_length=config.PATHWAYS_PER_CAREER_MIN, max_length=config.PATHWAYS_PER_CAREER_MAX
    )
    salary_inr_lpa: SalaryBands
    growth_index: Unit
    job_velocity: Unit
    disruption_index: Unit
    stability: Unit
    risk_level: Unit
    prestige: Unit
    higher_studies_typical: bool
    city_demand: dict[CityId, Unit]
    adjacent_careers: list[str]
    sources: list[NonEmptyStr] = Field(min_length=1)
    data_note: NonEmptyStr

    @model_validator(mode="after")
    def structural_rules(self) -> Self:
        missing = set(config.CITIES) - set(self.city_demand)
        if missing:
            raise ValueError(f"city_demand is missing {sorted(missing)}")
        if not any(p.entry == "after_class_12" for p in self.pathways):
            raise ValueError("needs at least one after_class_12 pathway")
        ids = [p.id for p in self.pathways]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate pathway ids: {ids}")
        return self


# ---------------------------------------------------------------- §5 reference data
class Exam(StrictModel):
    id: NonEmptyStr
    name: NonEmptyStr
    level: ExamLevel
    domains: list[Domain] = Field(min_length=1)
    typical_month: Month
    source: NonEmptyStr


class Scholarship(StrictModel):
    id: NonEmptyStr
    name: NonEmptyStr
    provider: NonEmptyStr
    income_max_inr: PositiveInt | None  # None = no income limit (merit-only scheme)
    levels: list[StudyLevel] = Field(min_length=1)
    domains: list[Domain] = Field(min_length=1)
    amount_inr_per_year: PositiveInt
    restricted_to: str | None  # None = open to every student; otherwise who it is for
    source: NonEmptyStr


class City(StrictModel):
    id: CityId
    name: NonEmptyStr
    state: NonEmptyStr
    top_sectors: list[NonEmptyStr] = Field(min_length=1)


class SkillVocabularyEntry(StrictModel):
    name: NonEmptyStr
    category: NonEmptyStr
    aptitude: AptitudeDimension | None  # §8 school track derives this skill from this aptitude


# ---------------------------------------------------------------- §5 question sets
class AptitudeItem(StrictModel):
    id: NonEmptyStr
    dimension: AptitudeDimension
    prompt: NonEmptyStr
    options: list[NonEmptyStr] = Field(min_length=2)
    answer: NonNegativeInt

    @model_validator(mode="after")
    def one_valid_answer(self) -> Self:
        if self.answer >= len(self.options):
            raise ValueError(f"{self.id}: answer index {self.answer} is out of range")
        if len(set(self.options)) != len(self.options):
            raise ValueError(f"{self.id}: options must be distinct")
        return self


class RiasecItem(StrictModel):
    id: NonEmptyStr
    dimension: RiasecDimension
    prompt: NonEmptyStr


class WorkstyleItem(StrictModel):
    id: NonEmptyStr
    dimension: WorkstyleDimension
    prompt: NonEmptyStr


class FreeTextPrompt(StrictModel):
    id: FreeTextId
    prompt: NonEmptyStr


class QuestionSet(StrictModel):
    track: Track
    aptitude: list[AptitudeItem]
    riasec: list[RiasecItem]
    workstyle: list[WorkstyleItem]
    free_text: list[FreeTextPrompt]
    skills: list[NonEmptyStr] | None = None  # college only

    @model_validator(mode="after")
    def section_sizes(self) -> Self:
        if len(self.aptitude) != config.APTITUDE_ITEMS_TOTAL:
            raise ValueError(f"expected {config.APTITUDE_ITEMS_TOTAL} aptitude items")
        for dim in config.APTITUDE_DIMENSIONS:
            if sum(i.dimension == dim for i in self.aptitude) != config.APTITUDE_ITEMS_PER_DIMENSION:
                raise ValueError(f"expected {config.APTITUDE_ITEMS_PER_DIMENSION} {dim} items")
        for dim in config.RIASEC_DIMENSIONS:
            if sum(i.dimension == dim for i in self.riasec) != config.RIASEC_ITEMS_PER_DIMENSION:
                raise ValueError(f"expected {config.RIASEC_ITEMS_PER_DIMENSION} RIASEC {dim} items")
        if len(self.riasec) != config.RIASEC_ITEMS_PER_DIMENSION * len(config.RIASEC_DIMENSIONS):
            raise ValueError("unexpected number of RIASEC items")
        if sorted(i.dimension for i in self.workstyle) != sorted(config.WORKSTYLE_DIMENSIONS):
            raise ValueError(f"workstyle needs one item each for {config.WORKSTYLE_DIMENSIONS}")
        if sorted(p.id for p in self.free_text) != sorted(config.FREE_TEXT_IDS):
            raise ValueError(f"free_text needs exactly {config.FREE_TEXT_IDS}")
        ids = [i.id for i in (*self.aptitude, *self.riasec, *self.workstyle)]
        if len(ids) != len(set(ids)):
            raise ValueError("question ids must be unique")
        if self.track == "college":
            if self.skills is None or len(set(self.skills)) != config.COLLEGE_SKILL_LIST_SIZE:
                raise ValueError(f"college set needs {config.COLLEGE_SKILL_LIST_SIZE} distinct skills")
        elif self.skills is not None:
            raise ValueError("school set must not have a skills list")
        return self


# ---------------------------------------------------------------- §6 inputs
class StudentBase(StrictModel):
    aptitude_answers: dict[str, NonNegativeInt] = {}
    riasec_answers: dict[str, LikertAnswer] = {}
    workstyle_answers: dict[str, LikertAnswer] = {}
    marks_percent: Annotated[float, Field(ge=0.0, le=config.MARKS_MAX)] | None = None
    favourite_subjects: list[NonEmptyStr] = []
    home_city: CityId
    preferred_cities: list[CityId] = []
    willing_to_relocate: bool
    wants_higher_studies: bool
    risk_tolerance: Level
    dream_career_id: str | None = None
    free_text_1: str = ""
    free_text_2: str = ""


class SchoolStudentInput(StudentBase):
    track: Literal["school"]
    current_class: Annotated[int, Field(ge=config.SCHOOL_CLASS_MIN, le=config.SCHOOL_CLASS_MAX)]
    stream: Stream | None = None

    @model_validator(mode="after")
    def stream_matches_class(self) -> Self:
        needs_stream = self.current_class >= config.STREAM_FROM_CLASS
        if needs_stream and self.stream is None:
            raise ValueError(f"stream is required from Class {config.STREAM_FROM_CLASS}")
        if not needs_stream and self.stream is not None:
            raise ValueError(f"stream applies only from Class {config.STREAM_FROM_CLASS}")
        return self


class CollegeStudentInput(StudentBase):
    track: Literal["college"]
    degree: NonEmptyStr
    year: Annotated[int, Field(ge=config.COLLEGE_YEAR_MIN, le=config.COLLEGE_YEAR_MAX)]
    self_rated_skills: dict[str, SkillRating] = {}


StudentInput = Annotated[SchoolStudentInput | CollegeStudentInput, Field(discriminator="track")]


class ParentInput(StrictModel):
    annual_income_inr: PositiveInt
    education_budget_inr: NonNegativeInt
    loan_willingness: Literal["none", "moderate", "high"]
    risk_appetite: Level
    preferred_domains: list[Domain] = []
    location_preference: Literal["near_home", "anywhere_india", "abroad_ok"]
    supports_higher_studies: bool
    top_priority: Literal["stability", "salary", "prestige", "happiness"]
    free_text: str = ""


# ---------------------------------------------------------------- §14 demo personas
class DemoProfile(StrictModel):
    id: NonEmptyStr
    name: NonEmptyStr
    summary: NonEmptyStr
    student: StudentInput
    parent: ParentInput


# ---------------------------------------------------------------- loaded dataset
class Dataset(BaseModel):
    careers: list[Career]
    exams: list[Exam]
    scholarships: list[Scholarship]
    cities: list[City]
    skills: list[SkillVocabularyEntry]
    questions_school: QuestionSet
    questions_college: QuestionSet
    demo_profiles: list[DemoProfile]


# ---------------------------------------------------------------- §13 API
class HealthResponse(BaseModel):
    status: Literal["ok"]
    system1: str
    llm: Literal["groq", "gemini", "none"]
    demo_mode: bool
