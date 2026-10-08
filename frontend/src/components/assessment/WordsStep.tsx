import { wordCount } from "../../lib/format";
import { Field, TextArea } from "../ui/Field";
import { FREE_TEXT_GOOD_WORDS } from "./steps";
import type { StepProps } from "./types";

const MAX_CHARACTERS = 1000;

export function WordsStep({ draft, update, questions }: StepProps) {
  return (
    <div className="flex flex-col gap-6">
      <p className="text-ink/80">
        Write in your own words, in English. A few sentences each ({FREE_TEXT_GOOD_WORDS} words or more) help the engine
        understand what you enjoy.
      </p>
      {questions.free_text.map((prompt) => {
        const text = draft[prompt.id];
        const words = wordCount(text);
        return (
          <Field
            key={prompt.id}
            label={prompt.prompt}
            optional
            hint={
              words >= FREE_TEXT_GOOD_WORDS
                ? `${words} words. That is plenty.`
                : `${words} of ${FREE_TEXT_GOOD_WORDS} suggested words.`
            }
          >
            {(control) => (
              <TextArea
                {...control}
                maxLength={MAX_CHARACTERS}
                value={text}
                onChange={(e) => update({ [prompt.id]: e.target.value })}
              />
            )}
          </Field>
        );
      })}
    </div>
  );
}
