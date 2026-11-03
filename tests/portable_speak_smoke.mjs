import assert from "node:assert/strict";
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

const server = path.resolve(process.argv[2], "speak", "mcp-server");
const require = createRequire(path.join(server, "package.json"));
const { Client } = await import(pathToFileURL(require.resolve("@modelcontextprotocol/sdk/client/index.js")));
const { StdioClientTransport } = await import(pathToFileURL(require.resolve("@modelcontextprotocol/sdk/client/stdio.js")));
const transport = new StdioClientTransport({
  command: process.execPath, args: [path.join(server, "index.mjs")], cwd: server, stderr: "pipe",
});
const client = new Client({ name: "portable-library-test", version: "1.0.0" });
try {
  await client.connect(transport);
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map(tool => tool.name).sort(), ["list_voices", "speak"]);
  const result = await client.callTool({ name: "list_voices", arguments: {} });
  assert.equal(Boolean(result.isError), false, JSON.stringify(result));
  assert.ok(result.content.some(item => item.type === "text" && item.text.length));
  console.log(JSON.stringify({ toolDiscovery: true, voiceListing: true, audibleSpeech: false }));
} finally {
  await client.close();
}
