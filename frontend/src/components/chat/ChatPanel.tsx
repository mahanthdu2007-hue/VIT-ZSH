import { type FormEvent, useEffect, useRef, useState } from "react";
import type { AssessmentResult, ChatMessage } from "../../api/client";
import { useChatHistory, useHealth, useSendChat } from "../../api/queries";
import { LLM_PROVIDER_NAMES } from "../../lib/labels";
import { SourceLinks } from "../dashboard/SourceLinks";
import { Button } from "../ui/Button";
import { ReplyVisual } from "./ReplyVisual";

type AskingAs = "student" | "parent";

type ChatPanelProps = {
  open: boolean;
  onClose: () => void;
  result: AssessmentResult;
  careerName: (careerId: string) => string;
  dreamCareerId?: string | null;
};

function suggestions(result: AssessmentResult, careerName: (id: string) => string, dream?: string | null): string[] {
  const top = result.ranking[0]?.name ?? "my top career";
  const second = result.ranking[1]?.name;
  const last =
    dream && result.ranking[0]?.career_id !== dream
      ? `Why not ${careerName(dream)}?`
      : second
        ? `Compare ${top} and ${second}`
        : "What are my stretch options?";
  return [
    `Why is ${top} ranked first?`,
    "What if our budget is ₹3,00,000?",
    "Which scholarships can I apply for?",
    "What should I learn first?",
    last,
  ];
}

/** §17 Ask PRISM: questions about these results, answered from the engine's numbers. Opens without animation. */
export function ChatPanel({ open, onClose, result, careerName, dreamCareerId }: ChatPanelProps) {
  const history = useChatHistory(result.id);
  const send = useSendChat(result.id);
  const health = useHealth();
  const [askingAs, setAskingAs] = useState<AskingAs>("student");
  const [draft, setDraft] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const messages: ChatMessage[] = history.data?.messages ?? [];

  useEffect(() => {
    if (open) input.current?.focus();
  }, [open]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [messages.length, send.isPending]);

  if (!open) return null;

  const ask = (text: string) => {
    const message = text.trim();
    if (!message || send.isPending) return;
    setDraft("");
    send.mutate({ assessment_id: result.id, message, asking_as: askingAs, selected_career_id: null });
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    ask(draft);
  };
  const provider = health.data?.llm && health.data.llm !== "none" ? LLM_PROVIDER_NAMES[health.data.llm] : null;

  return (
    <aside
      role="dialog"
      aria-labelledby="chat-heading"
      onKeyDown={(e) => e.key === "Escape" && onClose()}
      className="fixed inset-x-0 bottom-0 z-40 flex h-[85vh] flex-col rounded-t-xl border border-line bg-surface text-ink shadow-lg lg:inset-y-0 lg:left-auto lg:right-0 lg:h-full lg:w-[440px] lg:rounded-none"
    >
      <header className="flex items-start justify-between gap-3 border-b border-line p-4">
        <div>
          <h2 id="chat-heading" className="text-lg">
            Ask PRISM
          </h2>
          <fieldset className="mt-2 flex items-center gap-3 text-sm">
            <legend className="sr-only">Asking as</legend>
            <span className="text-ink/70">Asking as:</span>
            {(["student", "parent"] as const).map((who) => (
              <label key={who} className="flex items-center gap-1">
                <input
                  type="radio"
                  name="asking-as"
                  checked={askingAs === who}
                  onChange={() => setAskingAs(who)}
                />
                {who === "student" ? "Student" : "Parent"}
              </label>
            ))}
          </fieldset>
        </div>
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </header>

      <div className="flex-1 overflow-y-auto p-4" aria-live="polite">
        {messages.length === 0 && (
          <div>
            <p className="text-ink/80">Ask anything about these results. Try one of these:</p>
            <ul className="mt-3 flex flex-col gap-2">
              {suggestions(result, careerName, dreamCareerId).map((q) => (
                <li key={q}>
                  <button
                    type="button"
                    onClick={() => ask(q)}
                    className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-left hover:border-ink/40"
                  >
                    {q}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        <ol className="flex flex-col gap-3">
          {messages.map((m, i) => (
            <li key={i} className={m.who === "user" ? "self-end max-w-[85%]" : "max-w-[95%]"}>
              <div
                className={
                  m.who === "user" ? "rounded-lg bg-ink px-3 py-2 text-surface" : "rounded-lg bg-paper px-3 py-2"
                }
              >
                {m.text}
              </div>
              {m.reply && <ReplyVisual reply={m.reply} result={result} />}
              {m.reply?.whatif && (
                <p className="mt-1 text-sm text-ink/60">
                  Worked out by the What-If engine. Use "Try a what-if" on the dashboard to change more answers.
                </p>
              )}
              {m.reply && m.reply.sources.length > 0 && <SourceLinks citations={m.reply.sources} />}
            </li>
          ))}
        </ol>
        {send.isPending && (
          <p role="status" className="mt-3 text-ink/70">
            PRISM is typing…
          </p>
        )}
        {send.isError && (
          <p role="alert" className="mt-3 text-danger">
            Could not get an answer. Please try again.
          </p>
        )}
        <div ref={bottom} />
      </div>

      <form onSubmit={submit} className="border-t border-line p-4">
        <label htmlFor="chat-input" className="sr-only">
          Your question
        </label>
        <div className="flex gap-2">
          <input
            id="chat-input"
            ref={input}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Type your question"
            maxLength={1000}
            className="min-h-10 flex-1 rounded-lg border border-line px-3"
          />
          <Button type="submit" disabled={send.isPending || !draft.trim()}>
            Send
          </Button>
        </div>
        <p className="mt-2 text-sm text-ink/70">Answers use your results. Money values are indicative estimates.</p>
        {provider && <p className="text-sm text-ink/70">Your answers are sent to {provider} to write replies.</p>}
      </form>
    </aside>
  );
}
