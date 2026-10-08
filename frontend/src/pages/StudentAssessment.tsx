import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import type { QuestionSet, Track } from "../api/client";
import { useQuestions } from "../api/queries";
import { AboutYouStep } from "../components/assessment/AboutYouStep";
import { AptitudeStep } from "../components/assessment/AptitudeStep";
import { LikertStep } from "../components/assessment/LikertStep";
import { PreferencesStep } from "../components/assessment/PreferencesStep";
import { SkillsStep } from "../components/assessment/SkillsStep";
import { STEP_TITLES, type StepErrors, type StepKey, stepsFor, validateStep } from "../components/assessment/steps";
import type { StepProps } from "../components/assessment/types";
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
  return <StudentAssessmentForTrack key={track} track={track} />;
}

function StudentAssessmentForTrack({ track }: { track: Track }) {
  const questions = useQuestions(track);
  if (questions.isPending) return <p>Loading the questions…</p>;
  if (questions.isError) {
    return (
      <p className="text-danger" role="alert">
        Could not load the questions. Is the backend running on port 8000?
      </p>
    );
  }
  return <Wizard track={track} questions={questions.data} />;
}

function Wizard({ track, questions }: { track: Track; questions: QuestionSet }) {
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

  useEffect(() => {
    headingRef.current?.focus();
  }, [index]);

  useEffect(() => {
    if (failedAttempts > 0) errorSummaryRef.current?.focus();
  }, [failedAttempts]);

  const update = (patch: Partial<StudentDraft>) => {
    const next = { ...draft, ...patch };
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
  const props: StepProps = { draft, update, errors, questions };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <p className="text-sm text-ink/70">{track === "school" ? "School student" : "College student"} · student part</p>
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
        <StepBody step={step} props={props} />
      </Card>
      <div className="flex justify-between gap-3">
        <Button variant="secondary" onClick={() => (index === 0 ? navigate("/") : goTo(index - 1))}>
          Back
        </Button>
        <Button onClick={next}>{index < steps.length - 1 ? "Next" : "Continue to the parent part"}</Button>
      </div>
    </div>
  );
}

function StepBody({ step, props }: { step: StepKey; props: StepProps }) {
  const { draft, update, errors, questions } = props;
  switch (step) {
    case "about":
      return <AboutYouStep {...props} />;
    case "aptitude":
      return <AptitudeStep {...props} />;
    case "interests":
      return (
        <LikertStep
          intro="How much would you enjoy each of these activities?"
          items={questions.riasec}
          scale={LIKERT_INTEREST}
          answers={draft.riasec_answers}
          onChange={(riasec_answers) => update({ riasec_answers })}
          errors={errors}
        />
      );
    case "workstyle":
      return (
        <LikertStep
          intro="How much do you agree with each statement?"
          items={questions.workstyle}
          scale={LIKERT_AGREE}
          answers={draft.workstyle_answers}
          onChange={(workstyle_answers) => update({ workstyle_answers })}
          errors={errors}
        />
      );
    case "words":
      return <WordsStep {...props} />;
    case "preferences":
      return <PreferencesStep {...props} />;
    case "skills":
      return <SkillsStep {...props} />;
  }
}
