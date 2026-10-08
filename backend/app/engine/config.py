"""Every weight, threshold and constant used by the engine. Each cites its spec section."""

from typing import Final

# ---------------------------------------------------------------- §5 Data model
DOMAIN_MIN_CAREERS: Final[dict[str, int]] = {  # §5 minimum careers per domain
    "Technology": 10,
    "Engineering": 8,
    "Science": 6,
    "Health": 6,
    "Arts & Design": 8,
    "Finance & Maths": 6,
    "Hyper-local": 6,
}
CAREERS_TOTAL_MIN: Final[int] = 55  # §5 55–60 careers in total
CAREERS_TOTAL_MAX: Final[int] = 60  # §5
PATHWAYS_PER_CAREER_MIN: Final[int] = 2  # §5 every career has 2–4 pathways
PATHWAYS_PER_CAREER_MAX: Final[int] = 4  # §5
SCHOLARSHIPS_MIN: Final[int] = 25  # §5 25–35 scholarships
SCHOLARSHIPS_MAX: Final[int] = 35  # §5
SKILL_VOCABULARY_MIN: Final[int] = 50  # §5 shared vocabulary of "about 60" skills
SKILL_VOCABULARY_MAX: Final[int] = 70  # §5
APTITUDE_ITEMS_TOTAL: Final[int] = 12  # §5 12 aptitude items, 3 per dimension
RIASEC_ITEMS_PER_DIMENSION: Final[int] = 3  # §5 18 RIASEC items, 3 per letter
WORKSTYLE_DIMENSIONS: Final[tuple[str, ...]] = (  # §5 4 workstyle Likert items
    "creative", "stability_vs_excitement", "teamwork", "structure",
)
FREE_TEXT_IDS: Final[tuple[str, ...]] = ("free_text_1", "free_text_2")  # §5 / §6 2 prompts
COLLEGE_SKILL_LIST_SIZE: Final[int] = 20  # §5 the 20 most common skills in the dataset
REQUIREMENT_COSINE_MAX: Final[float] = 0.98  # §5 / §7.5 audit: centred cosine above this = near-identical
DEMO_PROFILE_COUNT: Final[int] = 3  # §5 / §14 three demo personas
DEMO_FREE_TEXT_MIN_WORDS: Final[int] = 30  # §14 demo free text is 30–60 words
DEMO_FREE_TEXT_MAX_WORDS: Final[int] = 60  # §14

# ---------------------------------------------------------------- §6 Inputs
FREE_TEXT_MIN_WORDS: Final[int] = 15  # §6 free text counts toward completeness if ≥ 15 words
SCHOOL_CLASS_MIN: Final[int] = 9  # §6 current class 9–12
SCHOOL_CLASS_MAX: Final[int] = 12  # §6
STREAM_FROM_CLASS: Final[int] = 11  # §6 stream required in Class 11–12
COLLEGE_YEAR_MIN: Final[int] = 1  # §6 college year of study
COLLEGE_YEAR_MAX: Final[int] = 5  # §6 longest common UG programme (e.g. B.Arch, MBBS)
LIKERT_MAX: Final[int] = 5  # §6 / §7.2 Likert answers 1–5 (normalised by (x − 1)/4)
MARKS_MAX: Final[float] = 100.0  # §6 marks in percent

# ---------------------------------------------------------------- §7.2 Vectorize & Normalize
STUDENT_DIMENSIONS: Final[tuple[str, ...]] = (  # §7.2 student vector S, 11 dims in order
    "numerical", "logical", "verbal", "spatial", "creative", "R", "I", "A", "S", "E", "C",
)
APTITUDE_DIMENSIONS: Final[tuple[str, ...]] = ("numerical", "logical", "verbal", "spatial")  # §7.2
RIASEC_DIMENSIONS: Final[tuple[str, ...]] = ("R", "I", "A", "S", "E", "C")  # §7.2
APTITUDE_ITEMS_PER_DIMENSION: Final[int] = 3  # §7.2 aptitude_dim = correct / 3
LIKERT_MIN: Final[int] = 1  # §7.2 Likert normalised as (x − 1) / 4
LIKERT_RANGE: Final[int] = 4  # §7.2
MARKS_SCALE: Final[float] = 100.0  # §7.2 marks / 100
LEVEL_VALUES: Final[dict[str, float]] = {"low": 0.2, "medium": 0.5, "high": 0.8}  # §7.2

# ---------------------------------------------------------------- §7.3 System 1 Decision Layer
DOMAINS: Final[tuple[str, ...]] = (  # §7.3 student_domain_affinity labels (§5 domains)
    "Technology", "Engineering", "Science", "Health",
    "Arts & Design", "Finance & Maths", "Hyper-local",
)
PARENT_CONCERNS: Final[tuple[str, ...]] = (  # §7.3 parent_concerns labels
    "financial burden", "job security", "distance from home",
    "social prestige", "child's happiness", "uncertainty about new fields",
)
SYSTEM1_FALLBACK_MODEL: Final[str] = "typeform/distilbert-base-uncased-mnli"  # §3 light fallback
ABSTAIN_MIN_CONFIDENCE: Final[float] = 0.45  # §7.3 abstain if confidence < 0.45
ABSTAIN_MIN_MARGIN: Final[float] = 0.15  # §7.3 abstain if margin < 0.15
KEYWORD_CONFIDENCE_CAP: Final[float] = 0.5  # §7.3 KeywordBackend confidence cap

# ---------------------------------------------------------------- §7.4 Financial Constraint Solver
LOAN_FACTOR: Final[dict[str, float]] = {"none": 0.0, "moderate": 0.5, "high": 1.0}  # §7.4
SCHOLARSHIP_CAP_FRACTION: Final[float] = 0.6  # §7.4 scholarship capped at 60% of cost_mid
SOLVER_LAMBDA: Final[float] = 0.6  # §7.4 λ in quality − λ·effective_cost/capacity
FF_WITHIN_BUDGET: Final[float] = 1.0  # §7.4 FF when cost ≤ budget
FF_STRETCH_PENALTY: Final[float] = 0.5  # §7.4 FF = 1 − 0.5·(cost − budget)/(capacity − budget)
FF_NEEDS_AID: Final[float] = 0.0  # §7.4 FF for needs_aid careers

# ---------------------------------------------------------------- §7.5 Career Matcher
MATCH_CENTRE: Final[float] = 0.5  # §7.5 centred cosine cos(S − 0.5, R − 0.5)
SF_WEIGHT_COSINE: Final[float] = 0.6  # §7.5
SF_WEIGHT_DOMAIN_AFFINITY: Final[float] = 0.25  # §7.5
SF_WEIGHT_ACADEMIC: Final[float] = 0.15  # §7.5

# ---------------------------------------------------------------- §7.6 Parent-Student Conflict Index
CONFLICT_WEIGHTS: Final[dict[str, float]] = {  # §7.6 dimension weights, sum 1
    "domain": 0.25,
    "risk": 0.15,
    "location": 0.15,
    "higher_studies": 0.15,
    "cost": 0.15,
    "stability_vs_passion": 0.15,
}
CONFLICT_STUDENT_TOP_DOMAINS: Final[int] = 3  # §7.6 student top-3 affinity domains
LOCATION_PREFERENCE_VALUE: Final[dict[str, float]] = {  # §7.6 parent location_preference
    "near_home": 0.0, "anywhere_india": 0.5, "abroad_ok": 1.0,
}
PRIORITY_STABILITY_VALUE: Final[dict[str, float]] = {  # §7.6 parent priority → stability
    "stability": 1.0, "salary": 0.7, "prestige": 0.6, "happiness": 0.2,
}
CONFLICT_INDEX_SCALE: Final[float] = 100.0  # §7.6 CI = 100·Σ w·mismatch
CONFLICT_TOP_HOTSPOTS: Final[int] = 2  # §7.6 top 2 hotspots
PA_DOMAIN_MATCH: Final[float] = 1.0  # §7.6 career domain in preferred_domains
PA_DOMAIN_MISMATCH: Final[float] = 0.3  # §7.6 otherwise
PA_WEIGHTS: Final[dict[str, float]] = {  # §7.6 PA weighted mean (equal weights, see DECISIONS.md)
    "domain": 0.2,
    "risk": 0.2,
    "location": 0.2,
    "priority": 0.2,
    "financial_fit": 0.2,
}
PARENT_CONCERN_THRESHOLD: Final[float] = 0.5  # §7.6 concern counts if probability > 0.5
PARENT_CONCERN_BOOST: Final[float] = 0.1  # §7.6 +0.1 weight to matching PA dimension
PARENT_CONCERN_DIMENSION: Final[dict[str, str]] = {  # §7.6 concern → PA dimension (DECISIONS.md)
    "financial burden": "financial_fit",
    "job security": "risk",
    "distance from home": "location",
    "social prestige": "priority",
    "child's happiness": "priority",
    "uncertainty about new fields": "domain",
}

# ---------------------------------------------------------------- §7.7 Market Intelligence
CITIES: Final[tuple[str, ...]] = (  # §5 / §7.7 all 8 cities
    "bengaluru", "mysuru", "chennai", "hyderabad", "pune", "delhi_ncr", "mumbai", "coimbatore",
)
MD_WEIGHT_LOCAL_DEMAND: Final[float] = 0.5  # §7.7 Industry Hiring Index
MD_WEIGHT_JOB_VELOCITY: Final[float] = 0.3  # §7.7
MD_WEIGHT_STABILITY: Final[float] = 0.2  # §7.7 weight on (1 − disruption_index)

# ---------------------------------------------------------------- §7.8 Composite score
G_WEIGHT_GROWTH_INDEX: Final[float] = 0.5  # §7.8 Growth
G_WEIGHT_TRAJECTORY: Final[float] = 0.3  # §7.8
G_WEIGHT_MOBILITY: Final[float] = 0.2  # §7.8
TRAJECTORY_DIVISOR: Final[float] = 5.0  # §7.8 clip((senior_mid/entry_mid − 1)/5, 0, 1)
MOBILITY_LOG2_DIVISOR: Final[float] = 3.0  # §7.8 clip(log2(entry_mid_inr/income)/3, 0, 1)
INR_PER_LPA: Final[int] = 100_000  # §7.8 entry_mid_inr = mean(entry LPA) × 100000

SCORE_POINTS: Final[dict[str, float]] = {  # §7.8 PRISM Score = 30·SF + 20·FF + 20·MD + 15·G + 15·PA
    "student_fit": 30.0,
    "financial_fit": 20.0,
    "market_demand": 20.0,
    "growth": 15.0,
    "parent_alignment": 15.0,
}
SCORE_DECIMALS: Final[int] = 1  # §7.8 one decimal place

CONFIDENCE_WEIGHT_COMPLETENESS: Final[float] = 0.4  # §7.8 confidence
CONFIDENCE_WEIGHT_SYSTEM1: Final[float] = 0.35  # §7.8
CONFIDENCE_WEIGHT_DATA: Final[float] = 0.25  # §7.8 career data completeness
SYSTEM1_ALL_ABSTAINED_CONFIDENCE: Final[float] = 0.3  # §7.8 used when every decision abstained
CONFIDENCE_SCALE: Final[float] = 100.0  # §7.8
CONFIDENCE_BAND_HIGH: Final[float] = 75.0  # §7.8 High ≥ 75
CONFIDENCE_BAND_MEDIUM: Final[float] = 55.0  # §7.8 Medium 55–74, Low < 55

RISK_LOCATION_DEMAND_THRESHOLD: Final[float] = 0.4  # §7.8 location risk = 1 if demand < 0.4
RISK_EDUCATION_COST_INCOME_YEARS: Final[float] = 4.0  # §7.8 clip(effective_cost/income/4, 0, 1)

# ---------------------------------------------------------------- §7.9 Ranking
TOP_CAREERS_LIMIT: Final[int] = 10  # §7.9 top 10
STRETCH_SF_QUANTILE: Final[float] = 0.75  # §7.9 stretch options: SF in the top quartile

# ---------------------------------------------------------------- §8 Skill gap
SKILL_RATING_SCALE: Final[float] = 100.0  # §8 college self-rating / 100
SCHOOL_SKILL_BASELINE: Final[float] = 0.2  # §8 school baseline for unmapped skills

# ---------------------------------------------------------------- §9 SWOT
SWOT_ITEMS_PER_QUADRANT: Final[int] = 3  # §9 top 3 strengths / gaps / opportunities

# ---------------------------------------------------------------- §10 ROI and alternatives
ROI_SALARY_SHARE: Final[float] = 0.25  # §10 break_even = effective_cost / (0.25 × entry_mid_inr)
DREAM_TOP_RANK: Final[int] = 5  # §10 alternatives if dream ranks outside top 5

# ---------------------------------------------------------------- §11 What-If
WHATIF_RANK_DELTA_THRESHOLD: Final[int] = 2  # §11 reason if moved ≥ 2 ranks
WHATIF_POINT_DELTA_THRESHOLD: Final[float] = 3.0  # §11 or ≥ 3 points
WHATIF_TARGET_MS: Final[int] = 300  # §11 latency target

# ---------------------------------------------------------------- §12 System 2 explanations
EMBEDDING_MODEL: Final[str] = "sentence-transformers/all-MiniLM-L6-v2"  # §3 / §12
EXPLAIN_TOP_N: Final[int] = 5  # §12 explain the top 5 careers + middle path
EXPLAIN_WHY_COUNT: Final[int] = 3  # §12 why[3]
EXPLAIN_WHY_NOT_COUNT: Final[int] = 2  # §12 why_not[2]
LLM_TEMPERATURE: Final[float] = 0.2  # §12
