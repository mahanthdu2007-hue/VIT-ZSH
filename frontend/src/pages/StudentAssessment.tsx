import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import type { QuestionSet, Track } from "../api/client";
import { useQuestions } from "../api/queries";
import { AboutYouStep } from "../components/assessment/AboutYouStep";
import { AptitudeStep } from "../components/assessment/AptitudeStep";
import { LikertStep } from "../components/assessment/LikertStep";
import { PreferencesStep } from "../components/assessment/PreferencesStep";
import { SkillsStep } from "../components/assessment/SkillsStep";
import {
  STEP_TITLES,
  type StepErrors,
  type StepKey,
  questionSetKnown,
  stepsFor,
  validateStep,
} from "../components/assessment/steps";
import type { BasicStepProps } from "../components/assessment/types";
import { WordsStep } from "../components/assessment/WordsStep";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Stepper } from "../components/ui/Stepper";
import { LIKERT_AGREE, LIKERT_INTEREST } from "../lib/labels";
import { type StudentDraft, emptyDraft, useDraft } from "../state/draft";
import { NotFound } from "./NotFound";

export type AssessmentLocationState = { resumeAtEnd?: boolean } | null;

function isTrack(value: string | undefined): value is Track {
  return value === "school" || value === "college";
}

export function StudentAssessment() {
  const { track } = useParams();
  if (!isTrack(track)) return <NotFound />;
  return <Wizard key={track} track={track} />;
}

function Wizard({ track }: { track: Track }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { draft: savedDraft, setDraft } = useDraft();
  const steps = stepsFor(track);
  const resumeAtEnd = (location.state as AssessmentLocationState)?.resumeAtEnd === true;

  const [draft, setLocalDraft] = useState<StudentDraft>(() =>
    savedDraft?.track === track ? savedDraft : emptyDraft(track),
  );
  const [index, setIndex] = useState(resumeAtEnd && savedDraft?.track === track ? steps.length - 1 : 0);
  const [errors, setErrors] = useState<StepErrors>({});
  const [triedNext, setTriedNext] = useState(false);
  const [failedAttempts, setFailedAttempts] = useState(0);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const errorSummaryRef = useRef<HTMLParagraphElement>(null);
  const step = steps[index] as StepKey;
  // §5 each path gets its own short question set, chosen by the class and stream on the about step.
  const questionQuery = useQuestions(track, draft.stream, questionSetKnown(draft));
  const questions = questionQuery.data;
  const waitingForQuestions = step !== "about" && questions === undefined;

  useEffect(() => {
    headingRef.current?.focus();
  }, [index]);

  useEffect(() => {
    if (failedAttempts > 0) errorSummaryRef.current?.focus();
  }, [failedAttempts]);

  const update = (patch: Partial<StudentDraft>) => {
    const streamChanged = "stream" in patch && patch.stream !== draft.stream;
    // A new stream means a different question set, so earlier puzzle and interest answers no longer apply.
    const next = { ...draft, ...patch, ...(streamChanged ? { aptitude_answers: {}, riasec_answers: {} } : {}) };
    setLocalDraft(next);
    setDraft(next);
    if (triedNext) setErrors(validateStep(step, next, questions));
  };

  const goTo = (nextIndex: number) => {
    setErrors({});
    setTriedNext(false);
    setIndex(nextIndex);
    window.scrollTo({ top: 0 });
  };

  const next = () => {
    if (waitingForQuestions) return;
    const found = validateStep(step, draft, questions);
    setErrors(found);
    setTriedNext(true);
    if (Object.keys(found).length > 0) {
      setFailedAttempts((n) => n + 1);
      return;
    }
    if (index < steps.length - 1) goTo(index + 1);
    else navigate(`/assess/${track}/parent`);
  };

  const errorCount = Object.keys(errors).length;
  const basicProps: BasicStepProps = { draft, update, errors };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <p className="text-sm text-ink/70">
          {questions?.label ?? (track === "school" ? "School student" : "College student")} · student part
        </p>
        <h1 ref={headingRef} tabIndex={-1} className="mt-1 text-xl focus-visible:outline-none">
          {STEP_TITLES[step]}
        </h1>
      </div>
      <Stepper steps={steps.map((s) => STEP_TITLES[s])} current={index} />
      <Card>
        {errorCount > 0 && (
          <p
            ref={errorSummaryRef}
            tabIndex={-1}
            role="alert"
            className="mb-6 rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 font-medium text-danger"
          >
            {errorCount === 1 ? "One answer is missing below." : `${errorCount} answers are missing below.`}
          </p>
        )}
        {step === "about" ? (
          <AboutYouStep {...basicProps} />
        ) : questions !== undefined ? (
          <StepBody step={step} props={basicProps} questions={questions} />
        ) : questionQuery.isError ? (
          <p className="text-danger" role="alert">
            Could not load the questions. Is the backend running on port 8000?
          </p>
        ) : (
          <p>Loading the questions…</p>
        )}
      </Card>
      <div className="flex justify-between gap-3">
        <Button variant="secondary" onClick={() => (index === 0 ? navigate("/") : goTo(index - 1))}>
          Back
        </Button>
        <Button onClick={next} disabled={waitingForQuestions}>
          {index < steps.length - 1 ? "Next" : "Continue to the parent part"}
        </Button>
      </div>
    </div>
  );
}

function StepBody({ step, props, questions }: { step: StepKey; props: BasicStepProps; questions: QuestionSet }) {
  const { draft, update, errors } = props;
  switch (step) {
    case "about":
      return <AboutYouStep {...props} />;
    case "aptitude":
      return <AptitudeStep {...props} questions={questions} />;
    case "interests":
      return (
        <div className="flex flex-col gap-10">
          <LikertStep
            intro="How much would you enjoy each of these activities?"
            items={questions.riasec}
            scale={LIKERT_INTEREST}
            answers={draft.riasec_answers}
            onChange={(riasec_answers) => update({ riasec_answers })}
            errors={errors}
          />
          <LikertStep
            intro="How much do you agree with each statement?"
            items={questions.workstyle}
            scale={LIKERT_AGREE}
            answers={draft.workstyle_answers}
            onChange={(workstyle_answers) => update({ workstyle_answers })}
            errors={errors}
          />
        </div>
      );
    case "plans":
      return (
        <div className="flex flex-col gap-10">
          <PreferencesStep {...props} />
          <WordsStep {...props} questions={questions} />
        </div>
      );
    case "skills":
      return <SkillsStep {...props} questions={questions} />;
  }
}
