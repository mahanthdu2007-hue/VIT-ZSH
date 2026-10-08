import type { QuestionSet, Track } from "../../api/client";
import type { StudentDraft } from "../../state/draft";

export type StepKey = "about" | "aptitude" | "interests" | "plans" | "skills";
export type StepErrors = Record<string, string>;

export const STEP_TITLES: Record<StepKey, string> = {
  about: "About you",
  aptitude: "Quick puzzles",
  interests: "What you enjoy",
  plans: "Your plans",
  skills: "Your skills",
};

export function stepsFor(track: Track): StepKey[] {
  const steps: StepKey[] = ["about", "aptitude", "interests", "plans"];
  return track === "college" ? [...steps, "skills"] : steps;
}

export const STREAM_FROM_CLASS = 11;
export const FREE_TEXT_GOOD_WORDS = 15;

const unanswered = (ids: string[], answers: Record<string, number>, message: string): StepErrors =>
  Object.fromEntries(ids.filter((id) => answers[id] === undefined).map((id) => [id, message]));

/** The about step decides which question set loads: college, Class 9–10, or Class 11–12 once a stream is chosen. */
export function questionSetKnown(draft: StudentDraft): boolean {
  if (draft.track === "college" || draft.current_class === null) return draft.track === "college";
  return draft.current_class < STREAM_FROM_CLASS || draft.stream !== null;
}

/** Inline errors for one step; an empty object means the step is complete. Question steps need the loaded set. */
export function validateStep(step: StepKey, draft: StudentDraft, questions: QuestionSet | undefined): StepErrors {
  const errors: StepErrors = {};
  switch (step) {
    case "about":
      if (draft.track === "school") {
        if (draft.current_class === null) errors.current_class = "Choose your class.";
        else if (draft.current_class >= STREAM_FROM_CLASS && draft.stream === null) errors.stream = "Choose your stream.";
      } else {
        if (draft.degree.trim() === "") errors.degree = "Type the name of your degree, for example B.Com.";
        if (draft.year === null) errors.year = "Choose your year of study.";
      }
      if (draft.marks_percent !== null && (draft.marks_percent < 0 || draft.marks_percent > 100)) {
        errors.marks_percent = "Marks must be between 0 and 100.";
      }
      if (draft.home_city === null) errors.home_city = "Choose your home city.";
      return errors;
    case "aptitude":
      if (questions === undefined) return errors;
      return unanswered(questions.aptitude.map((q) => q.id), draft.aptitude_answers, "Choose an answer. A guess is fine.");
    case "interests":
      if (questions === undefined) return errors;
      return {
        ...unanswered(questions.riasec.map((q) => q.id), draft.riasec_answers, "Choose how much you would enjoy this."),
        ...unanswered(questions.workstyle.map((q) => q.id), draft.workstyle_answers, "Choose how much you agree."),
      };
    case "plans":
      if (draft.willing_to_relocate === null) errors.willing_to_relocate = "Choose yes or no.";
      if (draft.wants_higher_studies === null) errors.wants_higher_studies = "Choose yes or no.";
      if (draft.risk_tolerance === null) errors.risk_tolerance = "Choose one option.";
      return errors;
    case "skills":
      return unanswered(questions?.skills ?? [], draft.self_rated_skills, "Choose a level. None is fine.");
  }
}
