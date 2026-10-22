import { Check, Clock3, Eraser, LockKeyhole, Sparkles, Undo2 } from "lucide-react";
import type { Chip } from "../types";
import { timeLeft } from "./ui";

interface Props {
  chip: Chip;
  kind: "saved" | "temporary" | "once" | "forgotten" | "used";
  onUndo?: (id: number) => void;
  undone?: boolean;
}

const styles: Record<Props["kind"], string> = {
  saved: "bg-indigo-50 text-indigo-800 ring-indigo-200 dark:bg-indigo-500/10 dark:text-indigo-200 dark:ring-indigo-500/30",
  temporary: "bg-white text-stone-700 ring-stone-300 dark:bg-stone-900 dark:text-stone-300 dark:ring-stone-700",
  once: "bg-red-50 text-red-700 ring-red-200 dark:bg-red-500/10 dark:text-red-300 dark:ring-red-500/30",
  forgotten: "bg-stone-100 text-stone-600 ring-stone-200 dark:bg-stone-800 dark:text-stone-300 dark:ring-stone-700",
  used: "bg-transparent text-stone-600 ring-stone-300 dark:text-stone-300 dark:ring-stone-700",
};

export default function MemoryChip({ chip, kind, onUndo, undone }: Props) {
  const name = chip.short ?? chip.label ?? chip.content ?? "detail";
  const icons = { saved: Check, temporary: Clock3, once: LockKeyhole, forgotten: Eraser, used: Sparkles };
  const Icon = icons[kind];
  const label = {
    saved: `Noted: ${name}`,
    temporary: `Remembering ${name}, ${timeLeft(chip.expires_at ?? null)}`,
    once: `Using once, then forgetting: ${name}`,
    forgotten: `Forgot: ${name}`,
    used: chip.content ?? name,
  }[kind];

  if (undone) {
    return (
      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs line-through ring-1 ring-inset ${styles.forgotten}`}>
        {name}
      </span>
    );
  }

  return (
    <span
      title={chip.reason ? `Why: ${chip.reason}` : undefined}
      className={`inline-flex max-w-full items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ring-1 ring-inset ${styles[kind]}`}
    >
      <Icon size={12} aria-hidden="true" className="shrink-0" />
      <span className="truncate">{label}</span>
      {chip.learned && <span className="shrink-0 opacity-70">(your usual choice)</span>}
      {(kind === "saved" || kind === "temporary") && chip.id && onUndo && (
        <button
          onClick={() => onUndo(chip.id!)}
          className="-mr-0.5 ml-0.5 inline-flex shrink-0 items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[11px] hover:bg-black/5 dark:hover:bg-white/10"
          title="Don't remember this"
        >
          <Undo2 size={11} /> Undo
        </button>
      )}
    </span>
  );
}
