import { ArrowUp } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Ask, ChatMessage, Zone } from "../types";
import MessageBubble from "./MessageBubble";
import ZoneSwitcher from "./ZoneSwitcher";

const STARTERS = [
  "I'm vegetarian and I love Japanese food.",
  "I'm in Seattle until Sunday.",
  "Suggest a restaurant for dinner tonight.",
];

interface Props {
  zone: Zone;
  onZoneChange: (zone: Zone) => void;
  hiddenCount: number;
  messages: ChatMessage[];
  onSend: (message: string) => void;
  onAnswer: (ask: Ask, choice: string) => void;
  onUndo: (id: number) => void;
  busy: boolean;
  answering: boolean;
  resolvedAs: Record<number, string>;
  undone: Set<number>;
  disabledReason?: string;
}

export default function ChatPanel(props: Props) {
  const { zone, messages, busy, disabledReason } = props;
  const [draft, setDraft] = useState("");
  const scroller = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  useEffect(() => {
    const el = input.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [draft]);

  function submit(value = draft) {
    const text = value.trim();
    if (!text || busy || disabledReason) return;
    props.onSend(text);
    setDraft("");
  }

  return (
    <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-stone-200 bg-white dark:border-stone-800 dark:bg-stone-900">
      <div className="border-b border-stone-100 px-4 py-3 dark:border-stone-800">
        <ZoneSwitcher zone={zone} onChange={props.onZoneChange} hiddenCount={props.hiddenCount} />
      </div>

      <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto px-4 sm:px-6" aria-live="polite">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center py-10 text-center">
            <h2 className="max-w-md font-serif text-3xl leading-tight tracking-tight text-stone-900 dark:text-stone-50">Tell me about yourself. I'll keep only what you'd want kept.</h2>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-stone-500 dark:text-stone-400">
              Everyday preferences are saved quietly. Anything sensitive, I ask about first. Card numbers and passwords are used
              once, then deleted. You'll see each decision under your message.
            </p>
            <div className="mt-6 flex max-w-lg flex-wrap justify-center gap-2">
              {STARTERS.map((text) => (
                <button
                  key={text}
                  onClick={() => submit(text)}
                  disabled={busy || !!disabledReason}
                  className="rounded-full border border-stone-200 px-3 py-1.5 text-sm text-stone-600 transition hover:border-indigo-300 hover:text-indigo-700 disabled:opacity-50 dark:border-stone-700 dark:text-stone-300 dark:hover:border-indigo-500 dark:hover:text-indigo-300"
                >
                  {text}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl py-2">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onAnswer={props.onAnswer}
                onUndo={props.onUndo}
                answering={props.answering}
                resolvedAs={props.resolvedAs}
                undone={props.undone}
              />
            ))}
            {busy && (
              <div className="my-4 flex items-center gap-1.5 px-1" aria-label="Thinking">
                {[0, 1, 2].map((i) => (
                  <span key={i} className="h-2 w-2 animate-bounce rounded-full bg-stone-300 dark:bg-stone-600" style={{ animationDelay: `${i * 120}ms` }} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <form
        className="border-t border-stone-100 p-3 dark:border-stone-800"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-stone-200 bg-stone-50 p-1.5 transition focus-within:border-indigo-300 focus-within:bg-white focus-within:ring-4 focus-within:ring-indigo-100 dark:border-stone-700 dark:bg-stone-800/50 dark:focus-within:bg-stone-900 dark:focus-within:ring-indigo-500/20">
          <label htmlFor="chat-input" className="sr-only">Message</label>
          <textarea
            id="chat-input"
            ref={input}
            rows={1}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            placeholder={disabledReason ?? `Message your assistant in ${zone[0].toUpperCase() + zone.slice(1)}…`}
            disabled={!!disabledReason}
            className="max-h-40 min-h-[40px] flex-1 resize-none bg-transparent px-2.5 py-2 text-[15px] text-stone-900 outline-none placeholder:text-stone-400 disabled:cursor-not-allowed dark:text-stone-100"
          />
          <button
            type="submit"
            disabled={busy || !draft.trim() || !!disabledReason}
            aria-label="Send"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-stone-900 text-stone-50 transition hover:bg-indigo-700 disabled:bg-stone-300 dark:bg-stone-100 dark:text-stone-900 dark:disabled:bg-stone-700"
          >
            <ArrowUp size={18} />
          </button>
        </div>
      </form>
    </section>
  );
}
