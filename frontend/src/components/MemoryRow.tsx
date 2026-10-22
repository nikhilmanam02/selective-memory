import { Check, Clock3, Trash2 } from "lucide-react";
import type { HubConnection, Memory } from "../types";
import { timeAgo, timeLeft } from "./ui";

interface Props {
  memory: Memory;
  apps: HubConnection[];
  highlighted: boolean;
  onAccess: (memory: Memory, visibility: Memory["visibility"], apps?: number[]) => void;
  onDelete: (memory: Memory) => void;
}

const OPTIONS: { value: Memory["visibility"]; label: string; hint: string }[] = [
  { value: "open", label: "Open to AIs", hint: "Every connected AI can use this" },
  { value: "custom", label: "Choose AIs", hint: "Only the AIs you tick can use this" },
  { value: "sensitive", label: "Sensitive", hint: "No AI app ever sees this" },
];

export default function MemoryRow({ memory, apps, highlighted, onAccess, onDelete }: Props) {
  const tone =
    memory.visibility === "sensitive"
      ? "border-l-rose-400"
      : memory.visibility === "custom"
        ? "border-l-amber-400"
        : "border-l-indigo-500";

  return (
    <li
      className={`group rounded-xl border border-l-4 bg-white px-4 py-3.5 transition-colors duration-700 dark:bg-stone-900 ${tone} ${
        highlighted ? "border-indigo-300 bg-indigo-50/60 dark:bg-indigo-500/10" : "border-stone-200 dark:border-stone-800"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0 flex-1 basis-64">
          <p className="font-serif text-[18px] leading-snug text-stone-900 dark:text-stone-50">{memory.content}</p>
          <p className="mt-1 flex flex-wrap items-center gap-x-1.5 text-xs text-stone-500 dark:text-stone-400">
            <span>From {memory.source}</span>
            <span aria-hidden="true">/</span>
            <span>{memory.use_count > 0 ? `used ${memory.use_count} ${memory.use_count === 1 ? "time" : "times"}, last ${timeAgo(memory.last_used_at)}` : `added ${timeAgo(memory.created_at)}`}</span>
            {memory.rule === "temporary" && (
              <span className="inline-flex items-center gap-1"><Clock3 size={11} /> {timeLeft(memory.expires_at)}</span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div role="radiogroup" aria-label="Who can use this" className="inline-flex rounded-lg bg-stone-100 p-0.5 dark:bg-stone-800">
            {OPTIONS.map((option) => {
              const active = memory.visibility === option.value;
              return (
                <button
                  key={option.value}
                  role="radio"
                  aria-checked={active}
                  title={option.hint}
                  onClick={() => {
                    if (active) return;
                    onAccess(memory, option.value, option.value === "custom" ? apps.map((a) => a.id) : undefined);
                  }}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                    active
                      ? option.value === "sensitive"
                        ? "bg-white text-rose-700 shadow-sm dark:bg-stone-900 dark:text-rose-300"
                        : "bg-white text-stone-900 shadow-sm dark:bg-stone-900 dark:text-stone-50"
                      : "text-stone-500 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100"
                  }`}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
          <button
            onClick={() => onDelete(memory)}
            className="rounded-lg p-1.5 text-stone-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10"
            aria-label={`Delete "${memory.content}"`}
            title="Delete permanently"
          >
            <Trash2 size={15} />
          </button>
        </div>
      </div>

      {memory.visibility === "custom" && (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-stone-500">Only these AIs:</span>
          {apps.length === 0 && <span className="text-xs text-stone-400">connect an AI app first</span>}
          {apps.map((app) => {
            const on = memory.apps.includes(app.id);
            return (
              <button
                key={app.id}
                role="checkbox"
                aria-checked={on}
                onClick={() => {
                  const next = on ? memory.apps.filter((id) => id !== app.id) : [...memory.apps, app.id];
                  onAccess(memory, next.length ? "custom" : "sensitive", next);
                }}
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs ring-1 ring-inset transition ${
                  on
                    ? "bg-amber-50 text-amber-900 ring-amber-300 dark:bg-amber-500/10 dark:text-amber-200 dark:ring-amber-500/40"
                    : "text-stone-400 ring-stone-200 line-through hover:text-stone-700 dark:ring-stone-700"
                }`}
              >
                {on && <Check size={11} />} {app.name}
              </button>
            );
          })}
        </div>
      )}
    </li>
  );
}
