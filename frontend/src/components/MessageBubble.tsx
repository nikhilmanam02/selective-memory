import type { Ask, ChatMessage } from "../types";
import AskCard from "./AskCard";
import MemoryChip from "./MemoryChip";
import SystemNotice from "./SystemNotice";

interface Props {
  message: ChatMessage;
  onAnswer: (ask: Ask, choice: string) => void;
  onUndo: (id: number) => void;
  answering: boolean;
  resolvedAs: Record<number, string>;
  undone: Set<number>;
}

export default function MessageBubble({ message, onAnswer, onUndo, answering, resolvedAs, undone }: Props) {
  if (message.role === "system") return <SystemNotice>{message.content}</SystemNotice>;
  if (message.role === "error") return <SystemNotice tone="error">{message.content}</SystemNotice>;

  const user = message.role === "user";
  const result = message.result;
  const memoryChips =
    user && result
      ? [
          ...result.auto_saved.map((chip) => (
            <MemoryChip
              key={`s${chip.id}`}
              chip={chip}
              kind={chip.rule === "temporary" ? "temporary" : "saved"}
              onUndo={onUndo}
              undone={chip.id !== undefined && undone.has(chip.id)}
            />
          )),
          ...result.use_once.map((chip, i) => <MemoryChip key={`o${i}`} chip={chip} kind="once" />),
          ...result.forgotten.map((chip, i) => <MemoryChip key={`f${i}`} chip={chip} kind="forgotten" />),
        ]
      : [];

  return (
    <article className={`my-4 flex flex-col ${user ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed ${
          user
            ? "rounded-br-md bg-stone-900 text-stone-50 dark:bg-stone-100 dark:text-stone-900"
            : "rounded-bl-md border border-stone-200 bg-white text-stone-800 dark:border-stone-800 dark:bg-stone-900 dark:text-stone-100"
        }`}
      >
        {message.content}
      </div>

      {memoryChips.length > 0 && <div className="mt-1.5 flex max-w-[85%] flex-wrap justify-end gap-1.5">{memoryChips}</div>}

      {!user && result && result.used_memories.length > 0 && (
        <div className="mt-1.5 flex max-w-[85%] flex-wrap items-center gap-1.5">
          <span className="text-xs text-stone-400">Used</span>
          {result.used_memories.map((memory) => (
            <MemoryChip key={memory.id} chip={{ ...memory, content: memory.content.replace(/^User('s)? /, "") }} kind="used" />
          ))}
        </div>
      )}

      {!user &&
        result?.asks.map((ask) => (
          <AskCard key={ask.id} ask={ask} onAnswer={onAnswer} disabled={answering} resolved={resolvedAs[ask.id]} />
        ))}
    </article>
  );
}
