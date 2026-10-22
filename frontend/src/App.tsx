import { KeyRound } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import ChatPanel from "./components/ChatPanel";
import AppsPage from "./components/AppsPage";
import ConnectionsPanel from "./components/ConnectionsPanel";
import DeletionReceipts from "./components/DeletionReceipts";
import Header, { type Page } from "./components/Header";
import MemoryDashboard from "./components/MemoryDashboard";
import SettingsPanel from "./components/SettingsPanel";
import VerifyDeletionModal from "./components/VerifyDeletionModal";
import { ZONE_META } from "./components/ui";
import { askChoiceLabel } from "./components/AskCard";
import {
  connectionIsActive,
  memoryVisibleIn,
  type Activity,
  type Ask,
  type ChatMessage,
  type Health,
  type HubConnection,
  type Memory,
  type Zone,
} from "./types";

function sessionKey() {
  try {
    const existing = sessionStorage.getItem("selective-memory-session");
    if (existing) return existing;
    const id = crypto.randomUUID();
    sessionStorage.setItem("selective-memory-session", id);
    return id;
  } catch {
    return crypto.randomUUID();
  }
}

const uid = () => crypto.randomUUID();

export default function App() {
  const [sessionId] = useState(sessionKey);
  const [zone, setZone] = useState<Zone>("personal");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [connections, setConnections] = useState<HubConnection[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [backendDown, setBackendDown] = useState(false);
  const [busy, setBusy] = useState(false);
  const [answering, setAnswering] = useState(false);
  const [resolvedAs, setResolvedAs] = useState<Record<number, string>>({});
  const [undone, setUndone] = useState<Set<number>>(new Set());
  const [highlighted, setHighlighted] = useState<Set<number>>(new Set());
  const [panel, setPanel] = useState<"connections" | "settings" | "receipts" | "verify" | null>(null);
  const [page, setPage] = useState<Page>("data");
  const [activity, setActivity] = useState<Activity[]>([]);
  const [memoriesVersion, setMemoriesVersion] = useState(0);

  const notice = (content: string, role: ChatMessage["role"] = "system") =>
    setMessages((current) => [...current, { id: uid(), role, content }]);

  const refreshMemories = useCallback(async () => {
    const next = await api.memories();
    setMemories((current) => {
      if (JSON.stringify(current) !== JSON.stringify(next)) setMemoriesVersion((v) => v + 1);
      return next;
    });
  }, []);
  const refreshConnections = useCallback(async () => setConnections(await api.connections()), []);

  const refreshAll = useCallback(async () => {
    try {
      const [h, log] = await Promise.all([api.health(), api.activity(), refreshMemories(), refreshConnections()]);
      setHealth(h);
      setActivity(log);
      setBackendDown(false);
    } catch {
      setBackendDown(true);
    }
  }, [refreshConnections, refreshMemories]);

  useEffect(() => {
    void refreshAll();
    // Poll so memories saved by connected AI apps (via MCP) show up live.
    const interval = window.setInterval(() => void refreshAll(), 3000);
    return () => window.clearInterval(interval);
  }, [refreshAll]);

  const hiddenCount = useMemo(
    () => memories.filter((m) => m.status === "active" && m.rule !== "one_time" && !memoryVisibleIn(m, zone, sessionId)).length,
    [memories, zone, sessionId],
  );

  function flash(ids: number[]) {
    if (!ids.length) return;
    setHighlighted(new Set(ids));
    window.setTimeout(() => setHighlighted(new Set()), 2500);
  }

  async function send(text: string) {
    setBusy(true);
    const userId = uid();
    setMessages((current) => [...current, { id: userId, role: "user", content: text }]);
    try {
      const result = await api.chat(sessionId, zone, text);
      setMessages((current) => [
        ...current.map((m) => (m.id === userId ? { ...m, result } : m)),
        { id: uid(), role: "assistant", content: result.reply, result },
        ...result.learned.map((l) => ({ id: uid(), role: "system" as const, content: l.message })),
      ]);
      await refreshMemories();
      flash([...result.used_memories.map((m) => m.id), ...result.auto_saved.map((c) => c.id!).filter(Boolean)]);
    } catch (error) {
      notice((error as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  function changeZone(next: Zone) {
    if (next === zone) return;
    setZone(next);
    const hidden = memories.filter((m) => m.status === "active" && m.rule !== "one_time" && !memoryVisibleIn(m, next, sessionId)).length;
    notice(`Now in ${ZONE_META[next].label}. ${hidden === 0 ? "All memories are usable." : `${hidden} ${hidden === 1 ? "memory is" : "memories are"} hidden from the AI here.`}`);
  }

  async function answer(id: number, category: string, suggestedZone: string, choice: string) {
    setAnswering(true);
    try {
      const result = await api.answer(id, choice, choice === "zone_only" ? suggestedZone : undefined);
      setResolvedAs((current) => ({
        ...current,
        [id]: choice === "decline" ? "Not remembered" : `Saved: ${askChoiceLabel(choice, suggestedZone).toLowerCase()}`,
      }));
      if (result.learned?.message) notice(result.learned.message);
      await refreshMemories();
      if (choice !== "decline") flash([id]);
    } catch (error) {
      notice((error as Error).message, "error");
    } finally {
      setAnswering(false);
    }
    void category;
  }

  const answerAsk = (ask: Ask, choice: string) => answer(ask.id, ask.category, ask.suggested_zone, choice);

  async function undo(id: number) {
    try {
      const result = await api.undo(id);
      setUndone((current) => new Set(current).add(id));
      if (result.learned?.message) notice(result.learned.message);
      await refreshMemories();
    } catch (error) {
      notice((error as Error).message, "error");
    }
  }

  async function deleteMemory(memory: Memory) {
    if (!window.confirm(`Delete “${memory.content}” permanently?`)) return;
    await api.deleteMemory(memory.id);
    await refreshMemories();
  }

  async function setAccess(memory: Memory, visibility: Memory["visibility"], appIds?: number[]) {
    await api.setAccess(memory.id, visibility, appIds);
    await refreshMemories();
    flash([memory.id]);
  }

  async function addMemory(content: string, visibility: "open" | "sensitive") {
    await api.addMemory({ content, short: content.slice(0, 40), category: "other", sensitivity: visibility === "sensitive" ? "high" : "low", zone: "global", visibility });
    await refreshMemories();
  }

  async function approveFromData(memory: Memory, choice: "open" | "sensitive" | "decline") {
    if (choice === "decline") {
      await api.answer(memory.id, "decline");
    } else {
      const zone = memory.zone === "global" ? "personal" : memory.zone;
      await api.answer(memory.id, "zone_only", zone, choice);
    }
    await refreshMemories();
    if (choice !== "decline") flash([memory.id]);
  }

  async function clearAll() {
    if (!window.confirm("Delete every memory and all chat history? This can't be undone.")) return;
    const result = await api.clearAll();
    setMessages([]);
    await refreshMemories();
    notice(`Deleted ${result.deleted} ${result.deleted === 1 ? "memory" : "memories"} and all chat history.`);
  }

  const claudeReady = health ? health.configured : null;
  const disabledReason = backendDown
    ? "Backend isn't running. Start it with: make dev"
    : claudeReady === false
      ? "Add your Anthropic API key to .env to start chatting"
      : undefined;

  return (
    <div className="flex h-[100dvh] flex-col bg-stone-50 text-stone-900 dark:bg-stone-950 dark:text-stone-100">
      <Header
        connectionCount={connections.length}
        activeConnections={connections.filter((c) => connectionIsActive(c)).length}
        page={page}
        onPage={setPage}
        onSettings={() => setPanel("settings")}
      />

      {(backendDown || claudeReady === false) && (
        <div className="mx-4 mb-3 flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 sm:mx-6 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
          <KeyRound size={18} className="mt-0.5 shrink-0" />
          {backendDown ? (
            <p><strong>The backend isn't running.</strong> In the VS Code terminal, run <code className="rounded bg-amber-100 px-1 dark:bg-amber-500/20">make dev</code>, then reload this page.</p>
          ) : (
            <p>
              <strong>Connect Claude to start chatting.</strong> Open the <code className="rounded bg-amber-100 px-1 dark:bg-amber-500/20">.env</code> file in the project folder, set{" "}
              <code className="rounded bg-amber-100 px-1 dark:bg-amber-500/20">ANTHROPIC_API_KEY=sk-ant-…</code>, save, and restart <code className="rounded bg-amber-100 px-1 dark:bg-amber-500/20">make dev</code>. Your memories and AI connections already work without it.
            </p>
          )}
        </div>
      )}

      {page === "apps" && (
        <AppsPage
          connections={connections}
          activity={activity}
          memoriesVersion={memoriesVersion}
          onConnect={() => setPanel("connections")}
          onChanged={refreshAll}
        />
      )}

      {page === "data" && (
        <MemoryDashboard
          memories={memories}
          apps={connections}
          highlighted={highlighted}
          onAdd={addMemory}
          onAccess={setAccess}
          onApprove={approveFromData}
          onDelete={deleteMemory}
          onConnect={() => setPanel("connections")}
          onReceipts={() => setPanel("receipts")}
          onVerify={() => setPanel("verify")}
          onClearAll={clearAll}
        />
      )}

      {page === "chat" && (
        <main className="mx-auto flex min-h-0 w-full max-w-4xl flex-1 px-4 pb-4 sm:px-6 sm:pb-6">
          <div className="min-h-0 min-w-0 flex-1">
            <ChatPanel
              zone={zone}
              onZoneChange={changeZone}
              hiddenCount={hiddenCount}
              messages={messages}
              onSend={send}
              onAnswer={answerAsk}
              onUndo={undo}
              busy={busy}
              answering={answering}
              resolvedAs={resolvedAs}
              undone={undone}
              disabledReason={disabledReason}
            />
          </div>
        </main>
      )}

      <ConnectionsPanel open={panel === "connections"} onClose={() => setPanel(null)} onCreated={refreshAll} />
      <SettingsPanel open={panel === "settings"} onClose={() => setPanel(null)} />
      <DeletionReceipts open={panel === "receipts"} onClose={() => setPanel(null)} />
      <VerifyDeletionModal open={panel === "verify"} onClose={() => setPanel(null)} />
    </div>
  );
}
