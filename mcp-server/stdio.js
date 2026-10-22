// stdio entry point, used by Claude Desktop.
// Claude Desktop starts this file itself; the token comes from the
// "env" block of claude_desktop_config.json (shown in the app's AI connections panel).
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createMcpServer, hubRequest } from "./tools.js";

const token = process.env.SELECTIVE_MEMORY_TOKEN;
if (!token) {
  console.error("SELECTIVE_MEMORY_TOKEN is missing. Create a connection in the Selective Memory app and copy its config.");
  process.exit(1);
}

// Fail soft: if the hub is offline we still start, and each tool call explains what to do.
hubRequest("/api/mcp/profile", token, null)
  .then((profile) => console.error(`Selective Memory: connected as "${profile.name}" (${profile.zone} zone)`))
  .catch((error) => console.error(`Selective Memory: ${error.message}`));

const server = createMcpServer(token);
await server.connect(new StdioServerTransport());
