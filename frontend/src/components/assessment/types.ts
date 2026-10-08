import type { QuestionSet } from "../../api/client";
import type { StudentDraft } from "../../state/draft";
import type { StepErrors } from "./steps";

export type StepProps = {
  draft: StudentDraft;
  update: (patch: Partial<StudentDraft>) => void;
  errors: StepErrors;
  questions: QuestionSet;
};
