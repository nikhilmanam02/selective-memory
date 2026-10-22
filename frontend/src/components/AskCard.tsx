import { Check, ShieldQuestion } from "lucide-react";
import type { Ask } from "../types";
import { ZONE_META, cap } from "./ui";

interface Props {
  ask: Ask;
  onAnswer: (ask: Ask, choice: string) => void;
  disabled?: boolean;
  resolved?: string;
}

export function askChoiceLabel(choice: string, zone: string) {
  if (choice === "zone_only") return `Only in ${ZONE_META[zone]?.label ?? cap(zone)}`;
  return { forever: "Remember forever", session: "Just this chat", decline: "Don't remember" }[choice] ?? choice;
}

export default function AskCard({ ask, onAnswer, disabled, resolved }: Props) {
  if (resolved) {
    return (
      <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-600 dark:bg-stone-800 dark:text-stone-300">
        <Check size={13} /> {resolved}
      </div>
    );
  }
  return (
    <section aria-label="Should I remember this?" className="mt-2 w-full max-w-xl rounded-2xl border border-amber-200 bg-amber-50/70 p-4 animate-rise dark:border-amber-500/30 dark:bg-amber-500/5">
      <div className="flex items-start gap-3">
        <div className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">
          <ShieldQuestion size={16} />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-stone-900 dark:text-stone-50">Should I remember this?</p>
          <p className="mt-1 font-serif text-[17px] text-stone-800 dark:text-stone-200">{ask.content}</p>
          <p className="mt-1 text-xs text-stone-500 dark:text-stone-400">{ask.reason}</p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 pl-11">
        {ask.options.map((choice) => (
          <button
            key={choice}
            disabled={disabled}
            onClick={() => onAnswer(ask, choice)}
            className={
              choice === "zone_only"
                ? "rounded-lg bg-stone-900 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-stone-700 disabled:opacity-50 dark:bg-white dark:text-stone-900 dark:hover:bg-stone-200"
                : choice === "decline"
                  ? "rounded-lg px-3 py-1.5 text-xs font-medium text-stone-500 transition hover:bg-stone-200/60 hover:text-stone-800 disabled:opacity-50 dark:hover:bg-stone-800 dark:hover:text-stone-200"
                  : "rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-xs font-medium text-stone-700 transition hover:bg-stone-50 disabled:opacity-50 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-200 dark:hover:bg-stone-800"
            }
          >
            {askChoiceLabel(choice, ask.suggested_zone)}
          </button>
        ))}
      </div>
    </section>
  );
}
