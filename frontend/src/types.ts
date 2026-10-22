export type Zone = "personal" | "work" | "health" | "finance";
export type MemoryZone = Zone | "global";
export type Rule = "forever" | "temporary" | "zone_only" | "one_time" | "session";

export interface Memory {
  id: number;
  content: string;
  short: string;
  source: string;
  category: string;
  zone: MemoryZone;
  rule: Rule;
  sensitivity: string;
  status: "active" | "pending";
  decision_reason: string | null;
  session_id: string | null;
  expires_at: string | null;
  created_at: string;
  last_used_at: string | null;
  use_count: number;
  shared: number;
  visibility: "open" | "sensitive" | "custom";
  apps: number[];
}

export interface Chip {
  id?: number;
  content?: string;
  short?: string;
  label?: string;
  rule?: string;
  zone?: string;
  reason?: string;
  expires_at?: string | null;
  learned?: boolean;
  memory_id?: number;
}

export interface Ask {
  id: number;
  content: string;
  category: string;
  suggested_zone: string;
  reason: string;
  options: string[];
}

export interface ChatResult {
  reply: string;
  used_memories: { id: number; content: string; rule: string; zone: string }[];
  auto_saved: Chip[];
  use_once: Chip[];
  asks: Ask[];
  forgotten: Chip[];
  learned: { category: string; message: string }[];
  withheld_counts: Record<string, number>;
  hidden_total?: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system" | "error";
  content: string;
  result?: ChatResult;
}

export interface Preference {
  category: string;
  behavior: string;
  zone: string | null;
  source: string;
}

export interface Receipt {
  id: number;
  memory_id: number;
  content_hash: string;
  category: string;
  rule: string;
  zone: string;
  reason: string;
  deleted_at: string;
}

export interface HubConnection {
  id: number;
  name: string;
  zone: Zone;
  zones: Zone[];
  can_write: boolean;
  created_at: string;
  last_used_at: string | null;
  token?: string;
}

export interface Activity {
  id: number;
  connection_id: number | null;
  app: string;
  action: "read" | "saved" | "asked" | "forgot" | "imported" | "blocked";
  count: number;
  note: string | null;
  created_at: string;
  memories: string[];
  deleted_count: number;
}

export interface Health {
  ok: boolean;
  configured: boolean;
  model: string | null;
}

export interface SetupInfo {
  project_root: string;
  node_path: string;
  stdio_script: string;
  mcp_url: string;
  public_url: string | null;
  claude_desktop_installed: boolean;
}

export function connectionIsActive(connection: HubConnection, now = Date.now()) {
  if (!connection.last_used_at) return false;
  const elapsed = now - Date.parse(connection.last_used_at);
  return Number.isFinite(elapsed) && elapsed >= 0 && elapsed < 5 * 60 * 1000;
}

/** Same rule as the backend's visible_to_app(): what one connected AI can read. */
export function visibleToApp(memory: Memory, appId: number, now = Date.now()) {
  if (memory.status !== "active" || memory.rule === "one_time" || memory.rule === "session") return false;
  if (memory.expires_at && Date.parse(memory.expires_at) <= now) return false;
  return memory.visibility === "open" || (memory.visibility === "custom" && memory.apps.includes(appId));
}

/** Same visibility rule as the backend's allowed_for(). */
export function memoryVisibleIn(memory: Memory, zone: Zone, sessionId: string) {
  if (memory.status !== "active") return false;
  if (memory.rule === "forever") return true;
  if (memory.rule === "temporary") return memory.zone === "global" || memory.zone === zone;
  if (memory.rule === "zone_only") return memory.zone === zone;
  return memory.session_id === sessionId;
}
