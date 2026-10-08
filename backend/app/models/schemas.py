from datetime import date
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


# ---------------------------------------------------------------- §7.2 engine: normalize
class StudentVector(BaseModel):
    values: dict[str, float]  # the 11 §7.2 dimensions, each in [0, 1]
    aptitude_correct: dict[str, int]  # correct answers per aptitude dimension
    defaulted: list[str]  # Likert dimensions with no answers, set to the neutral value


class StudentPreferences(BaseModel):
    risk_tolerance: float
    relocation: float
    higher_studies: float
    stability: float  # workstyle stability_vs_excitement item; 1 = prefers stability
    marks: float | None


class ParentPreferences(BaseModel):
    risk_appetite: float
    location: float
    higher_studies: float
    priority_stability: float


class Completeness(BaseModel):
    score: float
    answered: int
    total: int
    missing: list[str]


# ---------------------------------------------------------------- §7.4 engine: solver
CareerStatus = Literal["feasible", "needs_aid", "no_pathway"]


class PathwayEvaluation(BaseModel):
    pathway_id: str
    label: str
    entry: Entry
    institution_type: InstitutionType
    quality: float
    stage_fit: bool
    cost_mid: int
    scholarship: int
    scholarship_id: str | None
    scholarship_capped: bool
    effective_cost: int
    feasible: bool
    objective: float | None  # None when not a candidate for this student's stage


class CareerFinance(BaseModel):
    career_id: str
    status: CareerStatus
    chosen_pathway_id: str | None
    effective_cost: int | None
    financial_fit: float
    funding_gap: int
    budget: int
    capacity: int
    pathways: list[PathwayEvaluation]


# ---------------------------------------------------------------- §7.5 engine: matcher
class StudentFit(BaseModel):
    career_id: str
    centred_cosine: float
    domain_affinity: float
    academic_alignment: float
    student_fit: float


# ---------------------------------------------------------------- §7.3 System 1 decisions
class TypedDecision(BaseModel):
    question_id: str
    choice: str | None  # None when abstained
    probabilities: dict[str, float]
    confidence: float  # top probability
    margin: float  # top1 - top2
    abstained: bool
    backend: str


# ---------------------------------------------------------------- §7.6 engine: conflict
class ConflictDimension(BaseModel):
    name: str
    weight: float
    student_value: float | None
    parent_value: float | None
    mismatch: float
    points: float  # 100 · weight · mismatch


class ConflictResult(BaseModel):
    index: float
    dimensions: list[ConflictDimension]
    hotspots: list[str]
    student_top_domains: list[str]


class ParentAlignment(BaseModel):
    career_id: str
    components: dict[str, float]
    weights: dict[str, float]
    parent_alignment: float


class NashCandidate(BaseModel):
    career_id: str
    u_s: float
    u_p: float
    product: float


class MiddlePath(BaseModel):
    career_id: str
    method: Literal["nash", "max_min"]
    disagreement_s: float
    disagreement_p: float
    u_s: float
    u_p: float
    student_top_career_id: str
    student_change: float  # U_s(middle) − U_s(student's own top choice)
    parent_top_career_id: str
    parent_change: float  # U_p(middle) − U_p(parent's own top choice)
    student_gain: float  # U_s(middle) − d_s
    parent_gain: float  # U_p(middle) − d_p
    candidates: list[NashCandidate]  # best five by Nash product


# ---------------------------------------------------------------- §7.7–§7.9 engine: market, scoring
class MarketDemand(BaseModel):
    career_id: str
    local_demand: float
    best_city: str
    market_demand: float


class Growth(BaseModel):
    career_id: str
    trajectory: float
    mobility_uplift: float
    growth: float


class PrismScore(BaseModel):
    career_id: str
    score: float
    values: dict[str, float]  # each component in [0, 1]
    points: dict[str, float]  # points earned per component; they sum to score


class Confidence(BaseModel):
    score: float
    band: Literal["High", "Medium", "Low"]
    completeness: float
    system1_confidence: float
    data_completeness: float
    missing_inputs: list[str]


class RiskRadar(BaseModel):
    career_id: str
    financial: float
    skill_gap: float
    market: float
    location: float
    education_cost: float
    disruption: float


# ---------------------------------------------------------------- §8 engine: skills
class SkillGap(BaseModel):
    skill: str
    importance: float
    level_required: float
    current: float
    gap: float


class RoadmapStep(BaseModel):
    kind: Literal["pathway", "learning"]
    text: str
    skill: str | None = None


class TimelineYear(BaseModel):
    year: int
    steps: list[str]


class SkillPlan(BaseModel):
    career_id: str
    gaps: list[SkillGap]
    mean_gap: float
    roadmap: list[RoadmapStep]
    timeline: list[TimelineYear]


# ---------------------------------------------------------------- §9 engine: SWOT
class SwotItem(BaseModel):
    kind: str
    label: str
    value: float | None = None


class Swot(BaseModel):
    strengths: list[SwotItem]
    weaknesses: list[SwotItem]
    opportunities: list[SwotItem]
    threats: list[SwotItem]


# ---------------------------------------------------------------- §10 engine: ROI and alternatives
class Roi(BaseModel):
    career_id: str
    effective_cost: int
    entry_mid_inr: int
    salary_share: float
    break_even_years: float


class RankedAlternative(BaseModel):
    career_id: str
    score: float
    status: CareerStatus


class DreamAlternatives(BaseModel):
    dream_career_id: str
    reason: Literal["needs_aid", "outside_top"]
    alternatives: list[RankedAlternative]


class AidScholarship(BaseModel):
    scholarship_id: str
    name: str
    amount_inr_per_year: int
    restricted_to: str | None


class CheaperPathway(BaseModel):
    pathway_id: str
    effective_cost: int
    funding_gap: int


class StretchOption(BaseModel):
    career_id: str
    student_fit: float
    funding_gap: int
    cheapest_pathway_id: str
    scholarships: list[AidScholarship]
    cheaper_pathways: list[CheaperPathway]
    adjacent_feasible: list[str]


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


# ---------------------------------------------------------------- §7 pipeline trace
class IngestTrace(BaseModel):
    track: Track
    completeness: Completeness


class VectorizeTrace(BaseModel):
    student_vector: StudentVector
    student_preferences: StudentPreferences
    parent_preferences: ParentPreferences


class System1Trace(BaseModel):
    backend: str
    reused: bool  # True when the decisions came from an earlier run (What-If, demo cache)
    decisions: list[TypedDecision]
    domain_affinity: dict[str, float]
    parent_concerns: dict[str, float]


class SolverTrace(BaseModel):
    budget: int
    loan_factor: float
    capacity: int
    solver_lambda: float
    finances: list[CareerFinance]


class MatcherTrace(BaseModel):
    fits: list[StudentFit]


class ConflictTrace(BaseModel):
    conflict: ConflictResult
    concern_weights: dict[str, float]
    parent_alignment: list[ParentAlignment]
    middle_path: MiddlePath | None


class MarketTrace(BaseModel):
    markets: list[MarketDemand]


class ScoringTrace(BaseModel):
    growth: list[Growth]
    scores: list[PrismScore]
    confidence: list[Confidence]  # same order as scores
    risks: list[RiskRadar]  # careers with a pathway for the student's stage


class RankingTrace(BaseModel):
    order: list[str]  # every feasible career by score; the top list is the first ten
    top_career_ids: list[str]
    stretch_career_ids: list[str]
    dream_alternative_ids: list[str]


class PipelineTrace(BaseModel):
    ingest: IngestTrace
    vectorize: VectorizeTrace
    system1: System1Trace
    solver: SolverTrace
    matcher: MatcherTrace
    conflict: ConflictTrace
    market: MarketTrace
    scoring: ScoringTrace
    ranking: RankingTrace


# ---------------------------------------------------------------- §7.9 pipeline outputs
class RankedCareer(PrismScore):
    rank: int
    name: str
    domain: Domain


class CareerDetail(BaseModel):
    career: Career
    status: CareerStatus
    rank: int | None  # position among feasible careers by score; None if not feasible
    score: PrismScore
    student_fit: StudentFit
    finance: CareerFinance
    parent_alignment: ParentAlignment
    market: MarketDemand
    growth: Growth
    confidence: Confidence
    risk: RiskRadar
    skill_plan: SkillPlan
    roi: Roi
    pathway: Pathway  # chosen pathway (cheapest stage-fit pathway when needs_aid)
    scholarships: list[AidScholarship]  # schemes for this pathway, restricted ones included
    exams: list[Exam]  # entrance exams for this pathway


class PipelineResult(BaseModel):
    as_of: date
    ranking: list[RankedCareer]
    details: dict[str, CareerDetail]  # top careers, middle path, stretch options, dream alternatives
    conflict: ConflictResult
    middle_path: MiddlePath | None
    stretch_options: list[StretchOption]
    alternatives: DreamAlternatives | None
    swot: Swot | None
    confidence: Confidence | None  # confidence for the #1 career
    trace: PipelineTrace


# ---------------------------------------------------------------- §12 explanations
class Citation(BaseModel):
    """A dataset row an explanation used; the dashboard opens it from a source link."""
    kind: Literal["career", "pathway", "scholarship", "exam"]
    id: str
    career_id: str | None  # the career a pathway belongs to (pathway ids repeat across careers)
    label: str
    text: str  # the row as indexed for System 2 (§12)


class CareerExplanation(BaseModel):
    career_id: str
    why: list[str]
    why_not: list[str]
    roadmap_narrative: str
    cited_ids: list[str]
    citations: list[Citation]
    source: Literal["template", "llm"] = "template"


class GuardrailHit(BaseModel):
    """§12 a sentence with a number that is not in ENGINE_RESULT or CONTEXT."""
    career_id: str
    field: str  # e.g. "why[1]" or "roadmap_narrative"
    sentence: str
    unsupported: list[str]
    action: Literal["replaced", "removed"]
    replacement: str | None


class CareerExplainTrace(BaseModel):
    career_id: str
    source: Literal["template", "llm"]
    fallback_reason: str | None  # why the template was used for the whole career
    retrieved_ids: list[str]
    duration_ms: int


class System2Trace(BaseModel):
    provider: str
    model: str | None
    retrieval: Literal["chroma", "dataset", "none"]
    careers: list[CareerExplainTrace]
    guardrail_hits: list[GuardrailHit]
    duration_ms: int


class Explanations(BaseModel):
    source: Literal["template", "llm"]  # "llm" when any career's text came from the LLM
    status: Literal["pending", "ready"] = "ready"  # pending: LLM text is still being written (§13 lazy load)
    items: list[CareerExplanation]  # top 5 careers, then the middle path if not among them
    trace: System2Trace | None = None


# ---------------------------------------------------------------- §13 API
class DatasetCounts(BaseModel):
    careers: int
    scholarships: int
    exams: int
    cities: int
    demo_profiles: int


class HealthResponse(BaseModel):
    status: Literal["ok"]
    system1: str
    llm: Literal["gemini", "nvidia", "none"]  # §3 the active System 2 provider
    llm_model: str | None
    llm_requested: Literal["auto", "gemini", "nvidia", "none"]
    llm_notes: list[str]  # why auto mode skipped a provider
    demo_mode: bool
    dataset: DatasetCounts


class PublicAptitudeItem(StrictModel):
    id: str
    dimension: AptitudeDimension
    prompt: str
    options: list[str]


class PublicQuestionSet(StrictModel):
    """§13 question set as sent to the browser: aptitude answer keys stay on the server."""
    track: Track
    aptitude: list[PublicAptitudeItem]
    riasec: list[RiasecItem]
    workstyle: list[WorkstyleItem]
    free_text: list[FreeTextPrompt]
    skills: list[str] | None = None


class CareerSummary(BaseModel):
    id: str
    name: str
    domain: Domain
    steam: list[str]
    summary: str


class AssessRequest(StrictModel):
    student: StudentInput
    parent: ParentInput


class AssessmentResult(PipelineResult):
    id: str
    explanations: Explanations


class AssessmentInputs(BaseModel):
    """What a saved assessment needs to be re-run (§11): the inputs and the System 1 decisions."""
    student: StudentInput
    parent: ParentInput
    decisions: list[TypedDecision]
    as_of: date


class DemoCacheEntry(BaseModel):
    """§12 DEMO_MODE disk cache: a demo profile's full result and the System 1 decisions behind it."""
    decisions: list[TypedDecision]
    result: PipelineResult


class WhatIfOverrides(StrictModel):
    """§11 inputs a What-If may change; None = keep the original answer."""
    budget: NonNegativeInt | None = None
    loan_willingness: Literal["none", "moderate", "high"] | None = None
    home_city: CityId | None = None
    willing_to_relocate: bool | None = None
    risk_tolerance: Level | None = None
    risk_appetite: Level | None = None
    wants_higher_studies: bool | None = None
    top_priority: Literal["stability", "salary", "prestige", "happiness"] | None = None


class WhatIfRequest(StrictModel):
    assessment_id: str | None = None
    profile: AssessRequest | None = None
    overrides: WhatIfOverrides = WhatIfOverrides()

    @model_validator(mode="after")
    def one_base(self) -> Self:
        if (self.assessment_id is None) == (self.profile is None):
            raise ValueError("give exactly one of assessment_id or profile")
        return self


class CareerChange(BaseModel):
    career_id: str
    name: str
    status_before: CareerStatus
    status_after: CareerStatus
    rank_before: int | None  # among feasible careers; None if not feasible
    rank_after: int | None
    rank_change: int | None  # rank_before − rank_after (positive = moved up); None if either is None
    score_before: float
    score_after: float
    score_delta: float
    point_deltas: dict[str, float]  # from unrounded component values, so rounding never shows a fake change
    reason: str | None  # §11 set when the career moved ≥ 2 ranks or ≥ 3 points


class WhatIfResult(BaseModel):
    assessment_id: str | None
    overrides: WhatIfOverrides
    ranking: list[RankedCareer]
    changes: list[CareerChange]  # every career: new ranking first, then the rest in data order
    elapsed_ms: float


# ---------------------------------------------------------------- §17 Ask PRISM chat
ChatIntent = Literal["explain", "compare", "whatif", "scholarships", "plan", "other", "care"]


class ChatRequest(StrictModel):
    assessment_id: str
    message: str = Field(min_length=1, max_length=1000)
    asking_as: Literal["student", "parent"] = "student"
    selected_career_id: str | None = None


class ChatRoute(BaseModel):
    """§17 step 2 the router's output; overrides use the §11 fields."""
    intent: ChatIntent
    career_ids: list[str]
    overrides: WhatIfOverrides


class ChatWhatIf(BaseModel):
    """§17 a What-If asked in chat: exactly what /api/whatif returns for these overrides."""
    overrides: WhatIfOverrides
    result: WhatIfResult


class ChatReply(BaseModel):
    answer: str
    intent: ChatIntent
    sources: list[Citation]
    whatif: ChatWhatIf | None
    guardrail_hits: list[GuardrailHit]
    provider: str


class ChatMessage(BaseModel):
    who: Literal["user", "assistant"]
    text: str
    asking_as: Literal["student", "parent"]
    reply: ChatReply | None  # set on assistant messages


class ChatHistory(BaseModel):
    assessment_id: str
    messages: list[ChatMessage]
