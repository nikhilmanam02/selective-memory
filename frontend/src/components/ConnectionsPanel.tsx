import { Check, Copy, KeyRound } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import type { HubConnection, SetupInfo } from "../types";
import { Drawer, buttonPrimary, buttonSecondary, inputClass } from "./ui";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => Promise<void>;
}

type Client = "claude-desktop" | "claude-web" | "chatgpt" | "cursor" | "vscode";

const CLIENTS: { id: Client; label: string; web: boolean }[] = [
  { id: "claude-desktop", label: "Claude Desktop", web: false },
  { id: "claude-web", label: "Claude (web)", web: true },
  { id: "chatgpt", label: "ChatGPT", web: true },
  { id: "cursor", label: "Cursor", web: false },
  { id: "vscode", label: "VS Code", web: false },
];

export const IMPORT_PROMPT =
  "List everything you currently remember about me as short facts. Don't send anything yet. " +
  "After I approve the list, use the Selective Memory import_memories tool to send only the facts I approved. " +
  "Never include passwords, card numbers, codes or ID numbers.";

export const ALWAYS_CHECK =
  "I keep my personal memory in the Selective Memory app. Before answering anything personal (recommendations, plans, food, gifts, writing for me), call its recall_memories tool and follow what it returns. When I share a lasting fact about myself, save it with remember_fact.";

const WHERE_TO_PASTE: Record<string, string> = {
  "claude-desktop": "Claude: Settings → Profile → “What personal preferences should Claude consider in responses?”",
  "claude-web": "claude.ai: Settings → Profile → “What personal preferences should Claude consider in responses?”",
  chatgpt: "ChatGPT: Settings → Personalization → Custom instructions. Also turn off ChatGPT's own Memory there, so this is the only copy.",
  cursor: "Cursor: Settings → Rules → User Rules",
  vscode: "VS Code: a .github/copilot-instructions.md file, or Copilot's custom instructions setting",
};

const PUBLIC_URL_KEY = "selective-memory-public-url";

function readPublicUrl() {
  try {
    return localStorage.getItem(PUBLIC_URL_KEY) ?? "";
  } catch {
    return "";
  }
}

function instructionsFor(client: Client, token: string, setup: SetupInfo, publicUrl: string) {
  const base = publicUrl.replace(/\/+$/, "").replace(/\/mcp.*$/, "");
  const link = `${base}/mcp/${token}`;
  switch (client) {
    case "claude-desktop":
      return {
        steps: [
          "Open Claude Desktop → Settings → Developer → Edit Config.",
          'Paste this into claude_desktop_config.json. If the file already has "mcpServers", add only the "selective-memory" block inside it.',
          "Save, quit Claude completely (⌘Q) and open it again. You'll see the tools under the + menu.",
        ],
        copy: JSON.stringify(
          { mcpServers: { "selective-memory": { command: setup.node_path, args: [setup.stdio_script], env: { SELECTIVE_MEMORY_TOKEN: token } } } },
          null,
          2,
        ),
        copyLabel: "Copy config",
      };
    case "cursor":
      return {
        steps: ["Open Cursor → Settings → MCP → Add new MCP server (this edits ~/.cursor/mcp.json).", "Paste this in and save. The server shows a green dot when it's connected."],
        copy: JSON.stringify({ mcpServers: { "selective-memory": { url: setup.mcp_url, headers: { Authorization: `Bearer ${token}` } } } }, null, 2),
        copyLabel: "Copy config",
      };
    case "vscode":
      return {
        steps: ['In VS Code, run "MCP: Open User Configuration" from the Command Palette (⇧⌘P).', "Paste this in, save, and click Start above the server. Use Copilot Chat in Agent mode."],
        copy: JSON.stringify({ servers: { "selective-memory": { type: "http", url: setup.mcp_url, headers: { Authorization: `Bearer ${token}` } } } }, null, 2),
        copyLabel: "Copy config",
      };
    case "chatgpt":
      return {
        steps: [
          "In ChatGPT: Settings → Apps → Advanced settings → turn on Developer mode (Plus or Pro plan).",
          'Click "Create app". Name it Selective Memory, paste the link below as the MCP server URL, choose "No authentication", and create it.',
          "In a chat, open + → Developer mode and select Selective Memory.",
        ],
        copy: link,
        copyLabel: "Copy link",
      };
    case "claude-web":
      return {
        steps: [
          "On claude.ai: Customize → Connectors → Add custom connector.",
          'Name it Selective Memory, paste the link below as the server URL, choose "No sign-in" if asked, and click Add.',
          "In a chat, open + → Connectors and switch Selective Memory on. It also appears in Claude Desktop and mobile.",
        ],
        copy: link,
        copyLabel: "Copy link",
      };
  }
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      className={buttonSecondary}
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1600);
      }}
    >
      {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? "Copied" : label}
    </button>
  );
}

export default function ConnectionsPanel({ open, onClose, onCreated }: Props) {
  const [setup, setSetup] = useState<SetupInfo | null>(null);
  const [client, setClient] = useState<Client>("claude-desktop");
  const [canWrite, setCanWrite] = useState(true);
  const [publicUrl, setPublicUrl] = useState(readPublicUrl);
  const [created, setCreated] = useState<HubConnection | null>(null);
  const [error, setError] = useState("");
  const [installed, setInstalled] = useState<string | null>(null);
  const [installing, setInstalling] = useState(false);

  async function installClaude() {
    if (!created?.token) return;
    setInstalling(true);
    setError("");
    try {
      await api.installClaudeDesktop(created.token);
      setInstalled("Added. Now quit Claude Desktop completely (⌘Q) and open it again.");
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setInstalling(false);
    }
  }

  useEffect(() => {
    if (!open) return;
    setCreated(null);
    setInstalled(null);
    api.setup().then((info) => {
      setSetup(info);
      // A running `make tunnel` always wins: its address changes every time it starts.
      if (info.public_url) setPublicUrl(info.public_url);
    }).catch((reason: Error) => setError(reason.message));
  }, [open]);

  const meta = CLIENTS.find((c) => c.id === client)!;
  const needsPublic = meta.web && !/^https:\/\//.test(publicUrl.trim());

  async function create() {
    setError("");
    try {
      const result = await api.createConnection(meta.label, ["personal", "work", "health", "finance"], canWrite);
      setCreated(result);
      await onCreated();
    } catch (reason) {
      setError((reason as Error).message);
    }
  }

  const guide = created?.token && setup ? instructionsFor(client, created.token, setup, publicUrl.trim()) : null;

  return (
    <Drawer open={open} onClose={onClose} title="Connect an AI app" subtitle="It will read from this memory, only what you allow here." width="max-w-xl">
      {error && <p className="mb-4 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{error}</p>}

      {!guide ? (
        <div className="space-y-6">
          <section>
            <h3 className="text-sm font-medium text-stone-900 dark:text-stone-100">Which app?</h3>
            <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {CLIENTS.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setClient(c.id)}
                  className={`rounded-xl border px-3 py-2.5 text-left text-sm transition ${
                    client === c.id
                      ? "border-stone-900 bg-stone-900 text-white dark:border-stone-100 dark:bg-stone-100 dark:text-stone-900"
                      : "border-stone-200 text-stone-700 hover:border-stone-400 dark:border-stone-700 dark:text-stone-300"
                  }`}
                >
                  {c.label}
                  <span className="block text-[11px] opacity-60">{c.web ? "Needs a public link" : "Runs on this Mac"}</span>
                </button>
              ))}
            </div>
          </section>

          <section>
            <h3 className="text-sm font-medium text-stone-900 dark:text-stone-100">What can it see?</h3>
            <p className="mt-0.5 text-sm text-stone-500">Everything you've marked <strong className="font-medium text-stone-700 dark:text-stone-300">Open to AIs</strong>. Never anything sensitive. You can fine-tune any memory later on Your data.</p>
            <label className="mt-3 flex items-center gap-2 text-sm text-stone-700 dark:text-stone-300">
              <input type="checkbox" checked={canWrite} onChange={(e) => setCanWrite(e.target.checked)} className="h-4 w-4 accent-indigo-600" />
              Let it save new things it learns about me (sensitive ones still wait for my OK)
            </label>
          </section>

          {meta.web && (
            <section>
              <h3 className="text-sm font-medium text-stone-900 dark:text-stone-100">Public link to your Mac</h3>
              {setup?.public_url && publicUrl === setup.public_url ? (
                <p className="mt-0.5 text-xs text-indigo-700 dark:text-indigo-300">Picked up from your running <code>make tunnel</code>.</p>
              ) : (
                <p className="mt-0.5 text-xs leading-relaxed text-stone-500">
                  {meta.label} runs in the cloud, so it can't see localhost. In a new terminal run <code className="rounded bg-stone-100 px-1 dark:bg-stone-800">make tunnel</code>; the address fills in here automatically (reopen this panel).
                </p>
              )}
              <input
                className={`${inputClass} mt-2`}
                value={publicUrl}
                onChange={(e) => {
                  setPublicUrl(e.target.value);
                  try {
                    localStorage.setItem(PUBLIC_URL_KEY, e.target.value);
                  } catch {
                    /* private mode: just don't remember it */
                  }
                }}
                placeholder="https://something.trycloudflare.com"
              />
            </section>
          )}

          <button className={`${buttonPrimary} w-full`} onClick={create} disabled={needsPublic}>
            <KeyRound size={15} /> Connect {meta.label}
          </button>
        </div>
      ) : (
        <div className="space-y-5">
          <section className="rounded-2xl border border-indigo-200 bg-indigo-50/60 p-4 dark:border-indigo-500/30 dark:bg-indigo-500/5">
            <h3 className="font-serif text-xl text-stone-900 dark:text-stone-50">Add it to {meta.label}</h3>
            {client === "claude-desktop" && (
              <div className="mt-3 rounded-xl bg-white p-3 dark:bg-stone-900">
                {installed ? (
                  <p className="flex items-start gap-2 text-sm text-indigo-800 dark:text-indigo-200"><Check size={16} className="mt-0.5 shrink-0" /> {installed}</p>
                ) : (
                  <>
                    <button className={`${buttonPrimary} w-full`} onClick={installClaude} disabled={installing || setup?.claude_desktop_installed === false}>
                      {installing ? "Adding…" : "Add to Claude Desktop for me"}
                    </button>
                    <p className="mt-1.5 text-xs text-stone-500">
                      {setup?.claude_desktop_installed === false
                        ? "Claude Desktop isn't installed on this Mac. Get it at claude.ai/download, open it once, then come back."
                        : "Writes the config file for you and keeps a backup. Or do it by hand with the steps below."}
                    </p>
                  </>
                )}
              </div>
            )}
            <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-sm text-stone-700 dark:text-stone-300">
              {guide.steps.map((step) => <li key={step}>{step}</li>)}
            </ol>
            <div className="mt-3 flex justify-end"><CopyButton text={guide.copy} label={guide.copyLabel} /></div>
            <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-xl bg-stone-900 p-3 text-[12px] leading-relaxed text-stone-100">{guide.copy}</pre>
            <p className="mt-2 text-xs text-stone-600 dark:text-stone-400">
              This is shown once. {meta.web ? "Anyone with the link can read what you shared with this app, so keep it private." : "Keep it private."} You can disconnect it any time on the AI apps page.
            </p>
          </section>
          <section>
            <h3 className="text-sm font-medium text-stone-900 dark:text-stone-100">Make it automatic (once)</h3>
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
              Paste this into {WHERE_TO_PASTE[client]}. It's added to every chat, so you just talk normally and it follows your data.
            </p>
            <div className="mt-2 rounded-xl bg-stone-100 p-3 text-sm text-stone-700 dark:bg-stone-800 dark:text-stone-300">{ALWAYS_CHECK}</div>
            <div className="mt-2"><CopyButton text={ALWAYS_CHECK} label="Copy instruction" /></div>
          </section>
          <section>
            <h3 className="text-sm font-medium text-stone-900 dark:text-stone-100">Try it</h3>
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
              Ask {meta.label}: <span className="font-serif text-[16px] text-stone-900 dark:text-stone-100">“Suggest a few restaurants for dinner tonight.”</span> It checks your data first. Watch “What {meta.label} has” on Your data and the Activity list on AI apps.
            </p>
          </section>
          <section>
            <h3 className="text-sm font-medium text-stone-900 dark:text-stone-100">Bring over what it already knows</h3>
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">Paste this into {meta.label}. It lists its memories, you approve, then it sends only those.</p>
            <div className="mt-2 rounded-xl bg-stone-100 p-3 text-sm text-stone-700 dark:bg-stone-800 dark:text-stone-300">{IMPORT_PROMPT}</div>
            <div className="mt-2"><CopyButton text={IMPORT_PROMPT} label="Copy prompt" /></div>
          </section>
          <button className={`${buttonSecondary} w-full`} onClick={onClose}>Done</button>
        </div>
      )}
    </Drawer>
  );
}
