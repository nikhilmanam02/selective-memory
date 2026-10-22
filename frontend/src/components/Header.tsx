import { BrainCircuit, SlidersHorizontal } from "lucide-react";

export type Page = "data" | "chat" | "apps";

interface Props {
  page: Page;
  onPage: (page: Page) => void;
  connectionCount: number;
  activeConnections: number;
  onSettings: () => void;
}

export default function Header({ page, onPage, connectionCount, activeConnections, onSettings }: Props) {
  const tabs: { id: Page; label: string }[] = [
    { id: "data", label: "Your data" },
    { id: "chat", label: "Chat" },
    { id: "apps", label: "AI apps" },
  ];
  return (
    <header className="flex h-16 shrink-0 items-center justify-between gap-3 px-4 sm:px-6">
      <div className="flex min-w-0 items-center gap-6">
        <div className="flex items-center gap-2.5">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-stone-900 text-stone-50 dark:bg-stone-100 dark:text-stone-900">
            <BrainCircuit size={17} />
          </div>
          <h1 className="hidden font-serif text-xl tracking-tight text-stone-900 sm:block dark:text-stone-50">Selective Memory</h1>
        </div>
        <nav className="flex items-center gap-1" aria-label="Pages">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onPage(tab.id)}
              aria-current={page === tab.id ? "page" : undefined}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition ${
                page === tab.id
                  ? "bg-stone-200/70 font-medium text-stone-900 dark:bg-stone-800 dark:text-stone-50"
                  : "text-stone-500 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100"
              }`}
            >
              {tab.label}
              {tab.id === "apps" && connectionCount > 0 && (
                <span className="inline-flex items-center gap-1 text-xs text-stone-500">
                  {activeConnections > 0 && <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />}
                  {connectionCount}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>
      <button onClick={onSettings} className="rounded-xl p-2 text-stone-500 transition hover:bg-stone-200/60 hover:text-stone-800 dark:hover:bg-stone-800 dark:hover:text-stone-100" aria-label="Settings" title="How I handle your info">
        <SlidersHorizontal size={18} />
      </button>
    </header>
  );
}
