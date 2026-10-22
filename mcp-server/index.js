// Streamable HTTP MCP server on http://127.0.0.1:8001
//   POST /mcp          with header "Authorization: Bearer <key>"  (Cursor, VS Code)
//   POST /mcp/<key>    key inside the link                        (ChatGPT, claude.ai via a tunnel)
//   GET  /             status page
import express from "express";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { createMcpServer, hubRequest, apiOrigin } from "./tools.js";

const app = express();
const port = Number(process.env.MCP_PORT ?? 8001);
const host = process.env.MCP_HOST ?? "127.0.0.1";

app.use(express.json({ limit: "1mb" }));

async function profileFor(token) {
  if (!token) return null;
  try {
    return await hubRequest("/api/mcp/profile", token, null);
  } catch {
    return null;
  }
}

async function handle(req, res, token) {
  const profile = await profileFor(token);
  if (!profile) {
    res.status(401).json({ error: "Unknown or disconnected Selective Memory key. Create a new connection in the app." });
    return;
  }
  const server = createMcpServer(token);
  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
  res.on("close", () => {
    void transport.close();
    void server.close();
  });
  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    console.error("MCP request failed:", error.message);
    if (!res.headersSent) res.status(500).json({ error: "MCP request failed." });
  }
}

app.post("/mcp", (req, res) => {
  const header = req.headers.authorization ?? "";
  return handle(req, res, header.startsWith("Bearer ") ? header.slice(7) : "");
});
app.post("/mcp/:token", (req, res) => handle(req, res, req.params.token));

const notAllowed = (_req, res) => res.status(405).set("Allow", "POST").end();
app.get(["/mcp", "/mcp/:token"], notAllowed);
app.delete(["/mcp", "/mcp/:token"], notAllowed);

app.get("/health", (_req, res) => res.json({ ok: true, protocol: "MCP Streamable HTTP" }));

app.get("/", async (_req, res) => {
  let hub = "not reachable";
  try {
    const r = await fetch(`${apiOrigin}/api/health`);
    hub = r.ok ? "running" : "not reachable";
  } catch {}
  res.type("html").send(`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Selective Memory · MCP</title>
<body style="font-family:system-ui,sans-serif;max-width:560px;margin:64px auto;padding:0 20px;color:#1c1c19;line-height:1.55">
<h1 style="font-weight:500;font-size:24px">Selective Memory MCP server is running</h1>
<p>This address is for AI apps, not for people. There is nothing to click here.</p>
<p>Memory app: <b>${hub}</b> · Open <a href="http://localhost:5173">localhost:5173</a> and go to <b>AI apps</b> to connect Claude, ChatGPT, Cursor or VS Code.</p>
</body>`);
});

app.listen(port, host, () => {
  console.log(`Selective Memory MCP server: http://${host}:${port}  (AI apps connect to /mcp)`);
});
