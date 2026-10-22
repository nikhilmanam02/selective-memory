import { Cable, FileCheck2, Plus, ScanSearch, Search, ShieldQuestion, Trash } from "lucide-react";
import { useMemo, useState } from "react";
import { connectionIsActive, visibleToApp, type HubConnection, type Memory } from "../types";
import MemoryRow from "./MemoryRow";
import { buttonGhost, buttonPrimary, inputClass, timeAgo } from "./ui";

interface Props {
  memories: Memory[];
  apps: HubConnection[];
  highlighted: Set<number>;
  onAdd: (content: string, visibility: "open" | "sensitive") => Promise<void>;
  onAccess: (memory: Memory, visibility: Memory["visibility"], apps?: number[]) => void;
  onApprove: (memory: Memory, choice: "open" | "sensitive" | "decline") => void;
  onDelete: (memory: Memory) => void;
  onConnect: () => void;
  onReceipts: () => void;
  onVerify: () => void;
  onClearAll: () => void;
}

type View = { kind: "all" } | { kind: "app"; id: number } | { kind: "sensitive" };

function ViewCard({ active, title, count, note, onClick, dot }: { active: boolean; title: string; count: number; note: string; onClick: () => void; dot?: boolean }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`min-w-[160px] flex-1 rounded-2xl border px-4 py-3 text-left transition ${
        active
          ? "border-stone-900 bg-stone-900 text-stone-50 dark:border-stone-100 dark:bg-stone-100 dark:text-stone-900"
          : "border-stone-200 bg-white text-stone-900 hover:border-stone-400 dark:border-stone-800 dark:bg-stone-900 dark:text-stone-100"
      }`}
    >
      <p className={`flex items-center gap-1.5 text-sm ${active ? "opacity-80" : "text-stone-500 dark:text-stone-400"}`}>
        {dot && <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />}
        {title}
      </p>
      <p className="mt-1 font-serif text-3xl leading-none">{count}</p>
      <p className={`mt-1.5 text-xs ${active ? "opacity-70" : "text-stone-400"}`}>{note}</p>
    </button>
  );
}

export default function MemoryDashboard(props: Props) {
  const { memories, apps } = props;
  const [view, setView] = useState<View>({ kind: "all" });
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState("");
  const [draftVisibility, setDraftVisibility] = useState<"open" | "sensitive">("open");

  const active = memories.filter((m) => m.status === "active" && m.rule !== "one_time" && m.rule !== "session");
  const pending = memories.filter((m) => m.status === "pending");
  const sensitive = active.filter((m) => m.visibility === "sensitive");
  const viewApp = view.kind === "app" ? apps.find((a) => a.id === view.id) : undefined;

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return active.filter((m) => {
      if (view.kind === "sensitive" && m.visibility !== "sensitive") return false;
      if (view.kind === "app" && !visibleToApp(m, view.id)) return false;
      return !q || `${m.content} ${m.source}`.toLowerCase().includes(q);
    });
  }, [active, view, query]);

  async function add(event: React.FormEvent) {
    event.preventDefault();
    if (!draft.trim()) return;
    await props.onAdd(draft.trim(), draftVisibility);
    setDraft("");
  }

  const heading =
    view.kind === "app" ? `What ${viewApp?.name ?? "this AI"} has` : view.kind === "sensitive" ? "Sensitive: no AI sees these" : "All your data";

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 pb-16 sm:px-6">
        <section className="pb-6 pt-4">
          <h2 className="font-serif text-4xl tracking-tight text-stone-900 dark:text-stone-50">Your data</h2>
          <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-stone-500 dark:text-stone-400">
            Everything your AIs can know about you, in one place. Mark each thing open, sensitive, or only for the AIs you pick. ChatGPT, Claude and the rest read from here.
          </p>

          <form onSubmit={add} className="mt-5 flex flex-wrap gap-2 rounded-2xl border border-stone-200 bg-white p-2 dark:border-stone-800 dark:bg-stone-900">
            <label htmlFor="new-memory" className="sr-only">Something about you</label>
            <input
              id="new-memory"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Add something about you, e.g. I'm vegetarian and I love Japanese food"
              className="min-w-[220px] flex-1 bg-transparent px-3 py-2 text-[15px] text-stone-900 outline-none placeholder:text-stone-400 dark:text-stone-100"
              maxLength={300}
            />
            <div role="radiogroup" aria-label="Who can use it" className="inline-flex rounded-lg bg-stone-100 p-0.5 dark:bg-stone-800">
              {(["open", "sensitive"] as const).map((v) => (
                <button
                  key={v}
                  type="button"
                  role="radio"
                  aria-checked={draftVisibility === v}
                  onClick={() => setDraftVisibility(v)}
                  className={`rounded-md px-3 py-1.5 text-sm transition ${
                    draftVisibility === v
                      ? `bg-white font-medium shadow-sm dark:bg-stone-900 ${v === "sensitive" ? "text-rose-700 dark:text-rose-300" : "text-stone-900 dark:text-stone-50"}`
                      : "text-stone-500"
                  }`}
                >
                  {v === "open" ? "Open to AIs" : "Sensitive"}
                </button>
              ))}
            </div>
            <button type="submit" className={buttonPrimary} disabled={!draft.trim()}>
              <Plus size={15} /> Add
            </button>
          </form>
        </section>

        {pending.length > 0 && (
          <section className="mb-6 rounded-2xl border border-amber-200 bg-amber-50/70 p-4 dark:border-amber-500/30 dark:bg-amber-500/5">
            <h3 className="flex items-center gap-2 text-sm font-medium text-amber-900 dark:text-amber-200">
              <ShieldQuestion size={16} /> {pending.length === 1 ? "1 thing needs" : `${pending.length} things need`} your OK before it's kept
            </h3>
            <ul className="mt-3 space-y-2">
              {pending.map((memory) => (
                <li key={memory.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white p-3 dark:bg-stone-900">
                  <div className="min-w-0 flex-1 basis-64">
                    <p className="font-serif text-[18px] text-stone-900 dark:text-stone-50">{memory.content}</p>
                    <p className="mt-0.5 text-xs text-stone-500">From {memory.source}. {memory.decision_reason}</p>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <button onClick={() => props.onApprove(memory, "sensitive")} className="rounded-lg bg-stone-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-stone-700 dark:bg-white dark:text-stone-900">
                      Keep, sensitive
                    </button>
                    <button onClick={() => props.onApprove(memory, "open")} className="rounded-lg border border-stone-300 px-3 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-50 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800">
                      Keep, open to AIs
                    </button>
                    <button onClick={() => props.onApprove(memory, "decline")} className="rounded-lg px-3 py-1.5 text-xs font-medium text-stone-500 hover:bg-stone-100 hover:text-stone-800 dark:hover:bg-stone-800">
                      Don't keep
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="flex gap-3 overflow-x-auto pb-1" aria-label="Views">
          <ViewCard active={view.kind === "all"} title="All your data" count={active.length} note="Everything you've kept" onClick={() => setView({ kind: "all" })} />
          {apps.map((app) => (
            <ViewCard
              key={app.id}
              active={view.kind === "app" && view.id === app.id}
              title={`What ${app.name} has`}
              count={active.filter((m) => visibleToApp(m, app.id)).length}
              note={app.last_used_at ? `Last asked ${timeAgo(app.last_used_at)}` : "Hasn't asked yet"}
              dot={connectionIsActive(app)}
              onClick={() => setView({ kind: "app", id: app.id })}
            />
          ))}
          <ViewCard active={view.kind === "sensitive"} title="Sensitive" count={sensitive.length} note="No AI sees these" onClick={() => setView({ kind: "sensitive" })} />
          {apps.length === 0 && (
            <button onClick={props.onConnect} className="flex min-w-[180px] flex-1 items-center justify-center gap-2 rounded-2xl border border-dashed border-stone-300 px-4 py-3 text-sm text-stone-500 hover:border-stone-500 hover:text-stone-800 dark:border-stone-700">
              <Cable size={16} /> Connect ChatGPT or Claude
            </button>
          )}
        </section>

        <section className="mt-6">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h3 className="font-serif text-2xl text-stone-900 dark:text-stone-50">{heading}</h3>
            <div className="relative w-full sm:w-64">
              <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
              <input className={`${inputClass} pl-9`} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search" aria-label="Search your data" />
            </div>
          </div>
          {view.kind === "app" && (
            <p className="mt-1 text-sm text-stone-500">This is exactly what {viewApp?.name} gets when it asks about you. Mark something sensitive to take it away.</p>
          )}

          {shown.length === 0 ? (
            <div className="mt-4 rounded-2xl border border-dashed border-stone-300 px-6 py-12 text-center dark:border-stone-700">
              <p className="font-serif text-xl text-stone-800 dark:text-stone-200">
                {active.length === 0 ? "Nothing here yet" : view.kind === "app" ? `${viewApp?.name} can't see anything` : "Nothing matches"}
              </p>
              <p className="mx-auto mt-1 max-w-md text-sm text-stone-500">
                {active.length === 0
                  ? "Add something above, chat with your assistant, or connect an AI and bring over what it already knows."
                  : "Try another view or search."}
              </p>
            </div>
          ) : (
            <ul className="mt-4 space-y-2">
              {shown.map((memory) => (
                <MemoryRow
                  key={memory.id}
                  memory={memory}
                  apps={apps}
                  highlighted={props.highlighted.has(memory.id)}
                  onAccess={props.onAccess}
                  onDelete={props.onDelete}
                />
              ))}
            </ul>
          )}
        </section>

        <footer className="mt-8 flex flex-wrap items-center gap-1 border-t border-stone-200 pt-3 dark:border-stone-800">
          <button className={buttonGhost} onClick={props.onVerify}><ScanSearch size={14} /> Verify deletion</button>
          <button className={buttonGhost} onClick={props.onReceipts}><FileCheck2 size={14} /> Deletion receipts</button>
          <button className={`${buttonGhost} ml-auto hover:!bg-red-50 hover:!text-red-600 dark:hover:!bg-red-500/10`} onClick={props.onClearAll}>
            <Trash size={14} /> Delete everything
          </button>
        </footer>
      </div>
    </div>
  );
}
