import { ChevronDown, Link2Off, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import { connectionIsActive, type Activity, type HubConnection, type Memory } from "../types";
import { buttonPrimary, timeAgo } from "./ui";

interface Props {
  connections: HubConnection[];
  activity: Activity[];
  memoriesVersion: number;
  onConnect: () => void;
  onChanged: () => Promise<void>;
}

function describe(item: Activity) {
  const names = item.memories.length ? item.memories.map((m) => m.replace(/^User('s)? /, "")).join("; ") : "";
  const gone = item.deleted_count ? `${item.deleted_count} since deleted` : "";
  const list = [names, gone].filter(Boolean).join("; ");
  switch (item.action) {
    case "read":
      return { verb: `read ${item.count} ${item.count === 1 ? "memory" : "memories"}`, detail: list || "nothing it was allowed to see", ask: item.note };
    case "saved":
      return { verb: "saved a memory", detail: list };
    case "asked":
      return { verb: "sent something sensitive", detail: list ? `${list} is waiting for your OK on the Chat page` : "waiting for your OK" };
    case "forgot":
      return { verb: "deleted memories", detail: item.note ?? "" };
    case "imported":
      return { verb: "imported its memories", detail: item.note ?? "" };
    case "blocked":
      return { verb: "was blocked", detail: `${item.note ?? "Tried to change memory"}; it isn't allowed to save` };
  }
}

function AppCard({ app, memoriesVersion, onChanged }: { app: HubConnection; memoriesVersion: number; onChanged: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState<Memory[] | null>(null);
  const live = connectionIsActive(app);

  useEffect(() => {
    api.previewConnection(app.id).then(setPreview).catch(() => setPreview([]));
  }, [app.id, memoriesVersion]);

  async function disconnect() {
    if (!window.confirm(`Disconnect ${app.name}? It loses access immediately.`)) return;
    await api.revokeConnection(app.id);
    await onChanged();
  }

  return (
    <li className="rounded-2xl border border-stone-200 bg-white p-5 dark:border-stone-800 dark:bg-stone-900">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-serif text-xl text-stone-900 dark:text-stone-50">{app.name}</h3>
          <p className="mt-0.5 flex items-center gap-1.5 text-xs text-stone-500">
            <span className={`h-2 w-2 rounded-full ${live ? "bg-indigo-500" : "bg-stone-300 dark:bg-stone-600"}`} />
            {app.last_used_at ? (live ? `Active ${timeAgo(app.last_used_at)}` : `Last used ${timeAgo(app.last_used_at)}`) : "Not used yet"}
          </p>
        </div>
        <button onClick={disconnect} className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-stone-500 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10">
          <Link2Off size={14} /> Disconnect
        </button>
      </div>

      <p className="mt-3 text-sm text-stone-600 dark:text-stone-400">
        Reads everything marked <strong className="font-medium">Open to AIs</strong>, plus anything you chose for it. Never your sensitive data.
      </p>

      <label className="mt-4 flex items-center justify-between gap-3 text-sm text-stone-700 dark:text-stone-300">
        Can save new memories
        <button
          role="switch"
          aria-checked={app.can_write}
          onClick={async () => {
            await api.updateConnection(app.id, { can_write: !app.can_write });
            await onChanged();
          }}
          className={`relative h-6 w-10 rounded-full transition ${app.can_write ? "bg-indigo-600" : "bg-stone-300 dark:bg-stone-700"}`}
        >
          <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${app.can_write ? "left-[18px]" : "left-0.5"}`} />
        </button>
      </label>

      <button onClick={() => setOpen((v) => !v)} className="mt-4 flex w-full items-center justify-between rounded-xl bg-stone-100 px-3 py-2 text-left text-sm text-stone-700 hover:bg-stone-200/70 dark:bg-stone-800 dark:text-stone-300">
        <span>
          What {app.name} sees right now: <strong className="font-medium">{preview === null ? "…" : `${preview.length} ${preview.length === 1 ? "memory" : "memories"}`}</strong>
        </span>
        <ChevronDown size={16} className={`transition ${open ? "rotate-180" : ""}`} />
      </button>
      {open && preview && (
        <ul className="mt-2 space-y-1 border-l-2 border-stone-200 pl-3 dark:border-stone-700">
          {preview.length === 0 && <li className="text-sm text-stone-500">Nothing yet. Mark memories “Open to AIs” on Your data.</li>}
          {preview.map((m) => (
            <li key={m.id} className="font-serif text-[16px] text-stone-800 dark:text-stone-200">{m.content}</li>
          ))}
        </ul>
      )}
    </li>
  );
}

export default function AppsPage({ connections, activity, memoriesVersion, onConnect, onChanged }: Props) {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto px-4 pb-6 sm:px-6 lg:grid lg:grid-cols-[minmax(0,1fr)_400px] lg:overflow-hidden">
      <section className="shrink-0 lg:min-h-0 lg:overflow-y-auto lg:pr-2">
        <div className="flex flex-wrap items-end justify-between gap-3 pb-4 pt-2">
          <div className="max-w-xl">
            <h2 className="font-serif text-3xl tracking-tight text-stone-900 dark:text-stone-50">Your AI apps</h2>
            <p className="mt-1 text-sm leading-relaxed text-stone-500 dark:text-stone-400">
              Every app you connect reads from your data. What each one sees is set on Your data; here you connect apps, decide if they may add to it, and watch what they do.
            </p>
          </div>
          <button className={buttonPrimary} onClick={onConnect}><Plus size={15} /> Connect an app</button>
        </div>
        {connections.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-stone-300 p-10 text-center dark:border-stone-700">
            <p className="font-serif text-xl text-stone-900 dark:text-stone-100">No apps connected yet</p>
            <p className="mx-auto mt-2 max-w-md text-sm text-stone-500">
              Connect Claude, ChatGPT, Cursor or VS Code. Add “I'm vegetarian and I love Japanese food” on Your data, then ask the connected AI for restaurant ideas.
            </p>
            <button className={`${buttonPrimary} mt-5`} onClick={onConnect}><Plus size={15} /> Connect an app</button>
          </div>
        ) : (
          <ul className="grid gap-4 xl:grid-cols-2">
            {connections.map((app) => <AppCard key={app.id} app={app} memoriesVersion={memoriesVersion} onChanged={onChanged} />)}
          </ul>
        )}
      </section>

      <aside className="flex shrink-0 flex-col rounded-2xl lg:min-h-0 border border-stone-200 bg-white dark:border-stone-800 dark:bg-stone-900">
        <div className="border-b border-stone-100 px-5 py-4 dark:border-stone-800">
          <h2 className="font-serif text-2xl text-stone-900 dark:text-stone-50">Activity</h2>
          <p className="text-xs text-stone-500">Every time an app reads or changes your memory. Updates live.</p>
        </div>
        <ol className="px-5 py-3 lg:min-h-0 lg:flex-1 lg:overflow-y-auto">
          {activity.length === 0 && <li className="py-8 text-center text-sm text-stone-500">Nothing yet. Ask a connected app a question.</li>}
          {activity.map((item) => {
            const text = describe(item);
            return (
              <li key={item.id} className="border-b border-stone-100 py-3 last:border-0 dark:border-stone-800">
                <div className="flex items-baseline justify-between gap-2">
                  <p className="text-sm text-stone-800 dark:text-stone-200">
                    <strong className="font-medium">{item.app}</strong> {text.verb}
                  </p>
                  <time className="shrink-0 text-xs text-stone-400">{timeAgo(item.created_at)}</time>
                </div>
                {text.detail && <p className={`mt-0.5 text-sm ${item.action === "blocked" ? "text-red-600 dark:text-red-400" : "font-serif text-[15px] text-stone-600 dark:text-stone-400"}`}>{text.detail}</p>}
                {text.ask && <p className="mt-0.5 text-xs text-stone-400">For: “{text.ask}”</p>}
              </li>
            );
          })}
        </ol>
      </aside>
    </div>
  );
}
