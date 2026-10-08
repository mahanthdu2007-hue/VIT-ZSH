// Plain-language labels for engine ids, written from the student's or parent's point of view.
import type { CityId, Domain, Level, LoanWillingness, LocationPreference, Stream, TopPriority } from "../api/client";
import { componentColors } from "../theme/tokens";

export type ComponentKey = keyof typeof componentColors;

/** §7.8 PRISM Score components with their maximum points and a plain meaning. */
export const COMPONENTS: { key: ComponentKey; label: string; max: number; meaning: string }[] = [
  { key: "student_fit", label: "Student Fit", max: 30, meaning: "How well your answers match what this career needs." },
  { key: "financial_fit", label: "Financial Fit", max: 20, meaning: "How comfortably the family budget covers the course." },
  { key: "market_demand", label: "Market Demand", max: 20, meaning: "How much companies are hiring for it where you can work." },
  { key: "growth", label: "Growth", max: 15, meaning: "How pay and opportunities grow over a career." },
  { key: "parent_alignment", label: "Parent Alignment", max: 15, meaning: "How closely it matches what your parents hope for." },
];

export const CITY_NAMES: Record<CityId, string> = {
  bengaluru: "Bengaluru",
  mysuru: "Mysuru",
  chennai: "Chennai",
  hyderabad: "Hyderabad",
  pune: "Pune",
  delhi_ncr: "Delhi NCR",
  mumbai: "Mumbai",
  coimbatore: "Coimbatore",
};
export const CITY_IDS = Object.keys(CITY_NAMES) as CityId[];

export const DOMAIN_HINTS: Record<Domain, string> = {
  Technology: "Software, data and AI",
  Engineering: "Machines, electronics, buildings",
  Science: "Research and labs",
  Health: "Medicine and care",
  "Arts & Design": "Design, media and architecture",
  "Finance & Maths": "Money, numbers and analysis",
  "Hyper-local": "Farming tech, local industry, renewable energy",
};
export const DOMAINS = Object.keys(DOMAIN_HINTS) as Domain[];

export const STREAMS: Record<Stream, string> = {
  PCM: "Science with maths (PCM)",
  PCB: "Science with biology (PCB)",
  PCMB: "Science with maths and biology (PCMB)",
  Commerce: "Commerce",
  Humanities: "Humanities / arts",
};

export const SUBJECTS = [
  "Mathematics", "Physics", "Chemistry", "Biology", "Science", "Computer Science", "English",
  "Economics", "Accountancy", "Business Studies", "Business Statistics", "History", "Geography", "Art", "Music",
];

export const LEVEL_LABELS: Record<Level, string> = { low: "Low", medium: "Medium", high: "High" };

export const STUDENT_RISK_HINTS: Record<Level, string> = {
  low: "I want a safe, well-known path.",
  medium: "Some uncertainty is fine for a better fit.",
  high: "I'm happy to try something new and less certain.",
};

export const PARENT_RISK_HINTS: Record<Level, string> = {
  low: "We prefer a safe, well-known path.",
  medium: "Some uncertainty is fine if the fit is good.",
  high: "We're comfortable with a newer, less certain field.",
};

export const LOAN_LABELS: Record<LoanWillingness, string> = {
  none: "No loan",
  moderate: "A moderate loan",
  high: "A larger loan if needed",
};

export const LOCATION_LABELS: Record<LocationPreference, string> = {
  near_home: "Near home",
  anywhere_india: "Anywhere in India",
  abroad_ok: "Abroad is fine too",
};

export const PRIORITY_LABELS: Record<TopPriority, string> = {
  stability: "A stable job",
  salary: "A good salary",
  prestige: "A respected profession",
  happiness: "Our child's happiness",
};

export const LIKERT_INTEREST = ["Not at all", "A little", "Somewhat", "Quite a lot", "Very much"];
export const LIKERT_AGREE = ["Strongly disagree", "Disagree", "Not sure", "Agree", "Strongly agree"];

/** §7.6 conflict dimensions: a short name and a sentence describing which way the two sides differ. */
type Sides = { student_value?: number | null; parent_value?: number | null };

const studentHigher = (d: Sides) => (d.student_value ?? 0) > (d.parent_value ?? 0);

export const CONFLICT_DIMENSIONS: Record<string, { label: string; hotspot: (d: Sides) => string }> = {
  domain: {
    label: "Field of work",
    hotspot: () => "The fields the student enjoys most are not the ones the parents prefer.",
  },
  risk: {
    label: "Comfort with risk",
    hotspot: (d) =>
      studentHigher(d)
        ? "The student is more comfortable with an uncertain career than the parents are."
        : "The parents are more comfortable with an uncertain career than the student is.",
  },
  location: {
    label: "Where to live",
    hotspot: (d) =>
      studentHigher(d)
        ? "The student is ready to move away, while the parents prefer staying closer to home."
        : "The parents are open to moving further away than the student is.",
  },
  higher_studies: {
    label: "Higher studies",
    hotspot: (d) =>
      studentHigher(d)
        ? "The student wants to study further, but the parents are not planning for it."
        : "The parents would support further studies, but the student does not plan for them.",
  },
  cost: {
    label: "Cost",
    hotspot: () => "The student's top career costs more than the family budget.",
  },
  stability_vs_passion: {
    label: "Stability or passion",
    hotspot: (d) =>
      studentHigher(d)
        ? "The student wants more stability than the parents' top priority suggests."
        : "The parents put stability first, while the student leans towards exciting, less certain work.",
  },
};

const MISSING_GROUPS: { prefix: string; hint: string }[] = [
  { prefix: "aptitude:", hint: "Answer every aptitude question." },
  { prefix: "riasec:", hint: "Rate every activity in the interests step." },
  { prefix: "workstyle:", hint: "Answer every work style question." },
  { prefix: "skill:", hint: "Rate every skill in the skills step." },
];

const MISSING_FIELDS: Record<string, string> = {
  stream: "Add your stream.",
  marks_percent: "Add your latest marks.",
  favourite_subjects: "Pick your favourite subjects.",
  preferred_cities: "Choose the cities you would like to work in.",
  dream_career_id: "Pick a dream career, if you have one.",
  free_text_1: "Write a little more (15+ words) about something you made or did that you loved.",
  free_text_2: "Write a little more (15+ words) about your work in 10 years.",
  "parent.preferred_domains": "Parents: pick the fields you would like for your child.",
  "parent.free_text": "Parents: write a little more (15+ words) about your hopes and concerns.",
};

/** §7.8 missing_inputs → short hints, one per group, in the order the engine lists them. */
export function missingInputHints(missing: string[]): string[] {
  const hints = missing.map(
    (name) => MISSING_GROUPS.find((g) => name.startsWith(g.prefix))?.hint ?? MISSING_FIELDS[name] ?? `Add ${name}.`,
  );
  return [...new Set(hints)];
}

/** §7.2 student dimensions, as the student would describe them. */
export const DIMENSION_LABELS: Record<string, string> = {
  numerical: "Working with numbers",
  logical: "Logical reasoning",
  verbal: "Words and language",
  spatial: "Picturing shapes and spaces",
  creative: "Creativity",
  R: "Hands-on, practical work",
  I: "Investigating and solving problems",
  A: "Artistic, expressive work",
  S: "Helping and teaching people",
  E: "Leading and persuading",
  C: "Organising and keeping order",
};

/** §7.8 Risk Radar axes: a short name and what a high value means. */
export const RISK_AXES = [
  { key: "financial", label: "Money stretch", meaning: "How far the course pushes past the family budget." },
  { key: "skill_gap", label: "Skills to build", meaning: "How much the student still needs to learn." },
  { key: "market", label: "Fewer jobs", meaning: "How weak hiring is where the student can work." },
  { key: "location", label: "Distance from jobs", meaning: "How few jobs are near home if the student stays." },
  { key: "education_cost", label: "Cost against income", meaning: "Course cost compared with family income." },
  { key: "disruption", label: "Automation risk", meaning: "How much new technology may change this job." },
] as const;
