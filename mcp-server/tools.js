// Shared MCP tool definitions for both transports:
//   index.js -> HTTP (Cursor, VS Code, anything that speaks Streamable HTTP)
//   stdio.js -> stdio (Claude Desktop)
// Every tool is a thin call to the Python backend, which enforces zones,
// consent rules and deletion. This file never touches the database.
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

export const apiOrigin = process.env.HUB_API_ORIGIN ?? "http://127.0.0.1:8000";

export async function hubRequest(path, token, body) {
  let response;
  try {
    response = await fetch(`${apiOrigin}${path}`, {
      method: body ? "POST" : "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch {
    throw new Error(
      `Selective Memory isn't running at ${apiOrigin}. Start it with "make dev" and try again.`,
    );
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail ?? `Hub request failed (${response.status})`);
  }
  return payload;
}

function textResult(value) {
  return { content: [{ type: "text", text: JSON.stringify(value, null, 2) }] };
}

function errorResult(error) {
  return { isError: true, content: [{ type: "text", text: error.message }] };
}

const categories = [
  "preference",
  "identity",
  "relationship",
  "schedule",
  "location",
  "work",
  "health",
  "finance",
  "secret",
  "job_search",
  "other",
];

const factSchema = z.object({
  content: z.string().min(1).max(1000).describe('Third-person fact, e.g. "User is vegetarian"'),
  short: z.string().min(1).max(80).describe('1-4 word label, e.g. "vegetarian"'),
  category: z.enum(categories),
  sensitivity: z.enum(["low", "medium", "high"]).optional(),
  confidence: z.number().min(0).max(1).optional(),
  is_temporary: z.boolean().optional(),
  expires_in_hours: z.number().int().min(1).max(720).nullable().optional(),
  suggested_zone: z.enum(["global", "personal", "work", "health", "finance"]).nullable().optional(),
});

export function createMcpServer(token) {
  const server = new McpServer(
    { name: "selective-memory", version: "1.0.0" },
    {
      instructions:
        "Selective Memory is the user's personal memory. At the start of a conversation, and before " +
        "any recommendation or personal answer (food, places, gifts, plans, writing in their voice), " +
        "call recall_memories and apply every relevant fact it returns. When the user shares a lasting " +
        "fact about themselves, call remember_fact. When they ask you to forget something, call forget_memory.",
    },
  );
  const safely = (fn) => async (args) => {
    try {
      return textResult(await fn(args));
    } catch (error) {
      return errorResult(error);
    }
  };

  server.registerTool(
    "recall_memories",
    {
      title: "Recall what the user allows you to know",
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
      description:
        "Get the facts about the user that they have allowed this app to see (diet, tastes, " +
        "people, plans, work...). Call this at the START of every conversation and before any " +
        "recommendation or personal answer. Apply every relevant fact (e.g. vegetarian AND loves " +
        "Japanese food means only vegetarian-friendly Japanese places), and say which ones you used. " +
        "These facts replace any built-in memory. Never guess facts that are not returned.",
      inputSchema: {
        query: z.string().min(1).max(1000).describe("What you need context for, e.g. 'lunch ideas'"),
      },
    },
    safely(({ query }) => hubRequest("/api/mcp/recall", token, { query })),
  );

  server.registerTool(
    "remember_fact",
    {
      title: "Save a fact about the user",
      annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      description:
        "Send ONE lasting fact the user just shared about themselves to their memory hub " +
        "(preferences, people, plans, work, health...). The hub's privacy rules decide: " +
        "simple facts are saved, sensitive ones wait for the user's approval. Never send " +
        "passwords, card numbers, codes or ID numbers. Only say a fact was saved if the " +
        "result status is 'saved'; if it is 'needs_approval', tell the user to approve it " +
        "in the Selective Memory app.",
      inputSchema: { fact: factSchema },
    },
    safely(({ fact }) => hubRequest("/api/mcp/remember", token, { fact })),
  );

  server.registerTool(
    "forget_memory",
    {
      title: "Delete a memory",
      annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false },
      description:
        "Permanently delete memories that match what the user asked you to forget " +
        "(e.g. 'my Seattle trip'). Use only when the user explicitly asks to forget something.",
      inputSchema: {
        query: z.string().min(1).max(300).describe("What to forget, in the user's words"),
      },
    },
    safely(({ query }) => hubRequest("/api/mcp/forget", token, { query })),
  );

  server.registerTool(
    "import_memories",
    {
      title: "Move your built-in memories into the hub",
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: false },
      description:
        "Use only when the user asks to move what you remember about them into Selective " +
        "Memory. First show the user the facts you have, wait for them to approve, then send " +
        "only the approved facts (max 50). Never include secrets. Sensitive facts will wait " +
        "for approval in the hub.",
      inputSchema: {
        source: z.string().min(1).max(80).describe("Your app name, e.g. 'Claude Desktop'"),
        facts: z.array(factSchema).min(1).max(50),
      },
    },
    safely(({ source, facts }) => hubRequest("/api/mcp/import", token, { source, facts })),
  );

  return server;
}
