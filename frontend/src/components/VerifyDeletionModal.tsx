import { CircleCheck, CircleAlert } from "lucide-react";
import { useState } from "react";
import { api } from "../api";
import { Modal, buttonPrimary, inputClass } from "./ui";

export default function VerifyDeletionModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [text, setText] = useState("");
  const [result, setResult] = useState<{ matches: number; tables_checked: string[] } | null>(null);

  function close() {
    setText("");
    setResult(null);
    onClose();
  }

  return (
    <Modal open={open} onClose={close} title="Verify it's really gone">
      <p className="text-sm text-stone-500 dark:text-stone-400">
        Paste something you told me to forget (like a card number). I'll search every memory and every stored chat message for it.
      </p>
      <form
        className="mt-4 flex gap-2"
        onSubmit={async (e) => {
          e.preventDefault();
          if (text.trim()) setResult(await api.verifyDeletion(text.trim()));
        }}
      >
        <input autoFocus className={inputClass} value={text} onChange={(e) => { setText(e.target.value); setResult(null); }} placeholder="e.g. 4111 1111 1111 1111" />
        <button className={buttonPrimary} disabled={!text.trim()}>Search</button>
      </form>
      {result && (
        <div
          className={`mt-4 flex items-start gap-3 rounded-xl p-4 animate-pop ${
            result.matches === 0 ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-300" : "bg-red-50 text-red-800 dark:bg-red-500/10 dark:text-red-300"
          }`}
        >
          {result.matches === 0 ? <CircleCheck size={22} className="shrink-0" /> : <CircleAlert size={22} className="shrink-0" />}
          <div>
            <p className="text-base font-semibold">{result.matches === 0 ? "0 matches. It's gone." : `${result.matches} match${result.matches === 1 ? "" : "es"} found`}</p>
            <p className="mt-0.5 text-xs opacity-80">Searched memories, their sources, and all chat history.</p>
          </div>
        </div>
      )}
    </Modal>
  );
}
