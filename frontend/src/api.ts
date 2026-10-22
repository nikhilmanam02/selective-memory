import type {
  Activity,
  ChatResult,
  Health,
  HubConnection,
  Memory,
  Preference,
  Receipt,
  SetupInfo,
  Zone,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error("Can't reach the backend. Is it running? (make dev)");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(
      typeof detail === "string" ? detail : `Request failed (${response.status})`,
    );
  }
  return response.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  health: () => request<Health>("/health"),
  setup: () => request<SetupInfo>("/setup"),
  installClaudeDesktop: (token: string) =>
    post<{ ok: boolean; path: string }>("/claude-desktop/install", { token }),

  chat: (sessionId: string, zone: Zone, message: string) =>
    post<ChatResult>("/chat", { session_id: sessionId, zone, message }),

  memories: () => request<{ memories: Memory[] }>("/memories").then((r) => r.memories),
  addMemory: (input: { content: string; short: string; category: string; sensitivity: string; zone: string; visibility?: string }) =>
    post<{ status: string; reason?: string }>("/memories", input),
  answer: (id: number, choice: string, zone?: string, visibility?: "open" | "sensitive") =>
    post<{ learned: { message?: string } | null }>(`/memories/${id}/answer`, { choice, zone, visibility }),
  setAccess: (id: number, visibility: "open" | "sensitive" | "custom", apps?: number[]) =>
    request<{ memory: Memory }>(`/memories/${id}`, { method: "PATCH", body: JSON.stringify({ visibility, apps }) }),
  undo: (id: number) => post<{ learned: { message?: string } | null }>(`/memories/${id}/undo`),
  updateMemory: (id: number, changes: Record<string, unknown>) =>
    request<{ memory: Memory }>(`/memories/${id}`, { method: "PATCH", body: JSON.stringify(changes) }),
  deleteMemory: (id: number) => request(`/memories/${id}`, { method: "DELETE" }),
  clearAll: () => post<{ deleted: number }>("/data/clear"),

  preferences: () => request<{ preferences: Preference[] }>("/prefs").then((r) => r.preferences),
  setPreference: (category: string, behavior: string, zone?: string | null) =>
    request<{ preferences: Preference[] }>(`/prefs/${category}`, {
      method: "PUT",
      body: JSON.stringify({ behavior, zone: zone ?? null }),
    }).then((r) => r.preferences),
  resetPreferences: () => post("/prefs/reset"),

  receipts: () => request<{ receipts: Receipt[] }>("/receipts").then((r) => r.receipts),
  verifyDeletion: (text: string) =>
    post<{ matches: number; tables_checked: string[] }>("/verify-deletion", { text }),

  connections: () =>
    request<{ connections: HubConnection[] }>("/connections").then((r) => r.connections),
  createConnection: (name: string, zones: Zone[], canWrite: boolean) =>
    post<HubConnection>("/connections", { name, zones, can_write: canWrite }),
  updateConnection: (id: number, changes: { zones?: Zone[]; can_write?: boolean }) =>
    request<HubConnection>(`/connections/${id}`, { method: "PATCH", body: JSON.stringify(changes) }),
  previewConnection: (id: number) =>
    request<{ memories: Memory[] }>(`/connections/${id}/preview`).then((r) => r.memories),
  activity: () => request<{ activity: Activity[] }>("/activity").then((r) => r.activity),
  revokeConnection: (id: number) => request(`/connections/${id}`, { method: "DELETE" }),
};
