import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import type { Domain, Level, LoanWillingness, LocationPreference, ParentInput, StudentInput, TopPriority } from "../api/client";
import { useAssess } from "../api/queries";
import { FREE_TEXT_GOOD_WORDS } from "../components/assessment/steps";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { CheckboxGroup, RadioGroup, YES_NO } from "../components/ui/Choice";
import { Field, TextArea } from "../components/ui/Field";
import { MoneyInput } from "../components/ui/MoneyInput";
import { wordCount } from "../lib/format";
import {
  DOMAINS,
  DOMAIN_HINTS,
  LEVEL_LABELS,
  LOAN_LABELS,
  LOCATION_LABELS,
  PARENT_RISK_HINTS,
  PRIORITY_LABELS,
} from "../lib/labels";
import { toStudentInput, useDraft } from "../state/draft";
import type { AssessmentLocationState } from "./StudentAssessment";

type ParentDraft = {
  annual_income_inr: number | null;
  education_budget_inr: number | null;
  loan_willingness: LoanWillingness | null;
  risk_appetite: Level | null;
  preferred_domains: Domain[];
  location_preference: LocationPreference | null;
  supports_higher_studies: boolean | null;
  top_priority: TopPriority | null;
  free_text: string;
};

const EMPTY_PARENT: ParentDraft = {
  annual_income_inr: null,
  education_budget_inr: null,
  loan_willingness: null,
  risk_appetite: null,
  preferred_domains: [],
  location_preference: null,
  supports_higher_studies: null,
  top_priority: null,
  free_text: "",
};

const MAX_CHARACTERS = 1000;

function options<T extends string>(labels: Record<T, string>, hints?: Record<T, string>) {
  return (Object.keys(labels) as T[]).map((value) => ({ value, label: labels[value], hint: hints?.[value] }));
}

type Validation = { errors: Record<string, string>; input: ParentInput | null };

function validate(p: ParentDraft): Validation {
  const errors: Record<string, string> = {};
  if (p.annual_income_inr === null || p.annual_income_inr <= 0) errors.income = "Enter the yearly family income.";
  if (p.education_budget_inr === null) errors.budget = "Enter the total amount you can spend. 0 is allowed.";
  if (p.loan_willingness === null) errors.loan = "Choose one option.";
  if (p.risk_appetite === null) errors.risk = "Choose one option.";
  if (p.location_preference === null) errors.location = "Choose one option.";
  if (p.supports_higher_studies === null) errors.higher = "Choose yes or no.";
  if (p.top_priority === null) errors.priority = "Choose one option.";
  if (
    p.annual_income_inr === null || p.annual_income_inr <= 0 || p.education_budget_inr === null ||
    p.loan_willingness === null || p.risk_appetite === null || p.location_preference === null ||
    p.supports_higher_studies === null || p.top_priority === null
  ) {
    return { errors, input: null };
  }
  return {
    errors,
    input: {
      annual_income_inr: p.annual_income_inr,
      education_budget_inr: p.education_budget_inr,
      loan_willingness: p.loan_willingness,
      risk_appetite: p.risk_appetite,
      preferred_domains: p.preferred_domains,
      location_preference: p.location_preference,
      supports_higher_studies: p.supports_higher_studies,
      top_priority: p.top_priority,
      free_text: p.free_text.trim(),
    },
  };
}

export function ParentForm() {
  const { track } = useParams();
  const { draft } = useDraft();
  const student = draft && draft.track === track ? toStudentInput(draft) : null;
  const [handedOver, setHandedOver] = useState(false);

  if (!student) {
    return (
      <div className="mx-auto max-w-xl">
        <h1 className="text-xl">The student part comes first</h1>
        <p className="mt-2">Please answer the student questions, then hand the device to a parent.</p>
        <Link
          to={track === "college" ? "/assess/college" : "/assess/school"}
          className="mt-4 inline-block font-medium text-studentFit underline"
        >
          Start the student part
        </Link>
      </div>
    );
  }
  if (!handedOver) return <HandOver onContinue={() => setHandedOver(true)} />;
  return <ParentQuestions student={student} />;
}

function HandOver({ onContinue }: { onContinue: () => void }) {
  return (
    <Card className="mx-auto max-w-xl text-center">
      <h1 className="text-xl">Hand the device to your parent</h1>
      <p className="mt-3 text-ink/80">
        The student part is done. Now a parent answers a few questions about money, priorities and hopes. It takes
        about 3 minutes.
      </p>
      <Button className="mt-6" onClick={onContinue}>
        I'm the parent, let's start
      </Button>
    </Card>
  );
}

function ParentQuestions({ student }: { student: StudentInput }) {
  const navigate = useNavigate();
  const assess = useAssess();
  const [parent, setParent] = useState<ParentDraft>(EMPTY_PARENT);
  const [triedSubmit, setTriedSubmit] = useState(false);
  const [failedAttempts, setFailedAttempts] = useState(0);
  const summaryRef = useRef<HTMLParagraphElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => headingRef.current?.focus(), []);
  useEffect(() => {
    if (failedAttempts > 0) summaryRef.current?.focus();
  }, [failedAttempts]);

  const { errors, input } = validate(parent);
  const shown = triedSubmit ? errors : {};
  const errorCount = Object.keys(shown).length;
  const update = (patch: Partial<ParentDraft>) => setParent((current) => ({ ...current, ...patch }));
  const words = wordCount(parent.free_text);
  const backState: AssessmentLocationState = { resumeAtEnd: true };

  const submit = () => {
    setTriedSubmit(true);
    if (!input) {
      setFailedAttempts((n) => n + 1);
      return;
    }
    assess.mutate({ student, parent: input });
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <p className="text-sm text-ink/70">Parent part</p>
        <h1 ref={headingRef} tabIndex={-1} className="mt-1 text-xl focus-visible:outline-none">
          Your family's view
        </h1>
      </div>
      <Card>
        <form
          className="flex flex-col gap-6"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          {errorCount > 0 && (
            <p
              ref={summaryRef}
              tabIndex={-1}
              role="alert"
              className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 font-medium text-danger"
            >
              {errorCount === 1 ? "One answer is missing below." : `${errorCount} answers are missing below.`}
            </p>
          )}
          <MoneyInput
            label="Yearly family income"
            hint="Total household income in one year, in rupees, for example 7,00,000."
            value={parent.annual_income_inr}
            onChange={(annual_income_inr) => update({ annual_income_inr })}
            error={shown.income}
          />
          <MoneyInput
            label="Total budget for your child's education"
            hint="The whole amount you can spend on the course across all years, before any loan."
            value={parent.education_budget_inr}
            onChange={(education_budget_inr) => update({ education_budget_inr })}
            error={shown.budget}
          />
          <RadioGroup<LoanWillingness>
            legend="Would you take an education loan?"
            name="loan_willingness"
            options={options(LOAN_LABELS)}
            value={parent.loan_willingness}
            onChange={(loan_willingness) => update({ loan_willingness })}
            error={shown.loan}
          />
          <RadioGroup<Level>
            legend="How comfortable are you with risk in your child's career?"
            name="risk_appetite"
            options={options(LEVEL_LABELS, PARENT_RISK_HINTS)}
            value={parent.risk_appetite}
            onChange={(risk_appetite) => update({ risk_appetite })}
            error={shown.risk}
          />
          <CheckboxGroup<Domain>
            legend="Which fields would you like for your child?"
            hint="Pick any number, or none if you have no preference."
            options={DOMAINS.map((d) => ({ value: d, label: d, hint: DOMAIN_HINTS[d] }))}
            value={parent.preferred_domains}
            onChange={(preferred_domains) => update({ preferred_domains })}
          />
          <RadioGroup<LocationPreference>
            legend="Where would you like your child to study and work?"
            name="location_preference"
            options={options(LOCATION_LABELS)}
            value={parent.location_preference}
            onChange={(location_preference) => update({ location_preference })}
            error={shown.location}
          />
          <RadioGroup
            legend="Would you support studies after the first degree?"
            name="supports_higher_studies"
            options={YES_NO}
            value={parent.supports_higher_studies === null ? null : parent.supports_higher_studies ? "yes" : "no"}
            onChange={(value) => update({ supports_higher_studies: value === "yes" })}
            error={shown.higher}
          />
          <RadioGroup<TopPriority>
            legend="What matters most to you?"
            name="top_priority"
            options={options(PRIORITY_LABELS)}
            value={parent.top_priority}
            onChange={(top_priority) => update({ top_priority })}
            error={shown.priority}
          />
          <Field
            label="Your hopes and concerns"
            optional
            hint={`In your own words, in English. ${words} of ${FREE_TEXT_GOOD_WORDS} suggested words.`}
          >
            {(control) => (
              <TextArea
                {...control}
                maxLength={MAX_CHARACTERS}
                value={parent.free_text}
                onChange={(e) => update({ free_text: e.target.value })}
              />
            )}
          </Field>
          {assess.isError && (
            <p className="text-danger" role="alert">
              The assessment did not finish. Please check the answers and try again.
            </p>
          )}
          <div className="flex flex-wrap justify-between gap-3">
            <Button variant="secondary" onClick={() => navigate(`/assess/${student.track}`, { state: backState })}>
              Back to the student part
            </Button>
            <Button type="submit" disabled={assess.isPending}>
              {assess.isPending ? "Working out your results…" : "See our results"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
