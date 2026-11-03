#!/usr/bin/env node

// Copilot Speak — MCP server that provides a "speak" tool
// Uses Windows SAPI (System.Speech) via PowerShell for TTS

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const server = new Server(
  { name: "copilot-speak", version: "0.1.0" },
  { capabilities: { tools: {} } }
);

// Register available tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "speak",
      description:
        "Speak text aloud using Windows text-to-speech. " +
        "Use this to make Copilot talk through the speakers.",
      inputSchema: {
        type: "object",
        properties: {
          text: {
            type: "string",
            description: "The text to speak aloud",
          },
          rate: {
            type: "number",
            description:
              "Speech rate from -10 (slowest) to 10 (fastest). Default: 1",
            default: 1,
          },
          volume: {
            type: "number",
            description: "Volume from 0 (silent) to 100 (loudest). Default: 80",
            default: 80,
          },
        },
        required: ["text"],
      },
    },
    {
      name: "list_voices",
      description: "List available Windows TTS voices",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
  ],
}));

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "speak") {
    const text = args.text;
    const rate = args.rate ?? 1;
    const volume = args.volume ?? 80;

    // Escape single quotes for PowerShell
    const escaped = text.replace(/'/g, "''");

    const psScript = `
      Add-Type -AssemblyName System.Speech
      $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
      $synth.Rate = ${rate}
      $synth.Volume = ${volume}
      $synth.Speak('${escaped}')
      $synth.Dispose()
    `;

    try {
      await execFileAsync("powershell", ["-NoProfile", "-Command", psScript], {
        timeout: 60000,
      });
      return {
        content: [
          {
            type: "text",
            text: `✅ Spoke aloud: "${text.substring(0, 80)}${text.length > 80 ? "..." : ""}"`,
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          { type: "text", text: `❌ Speech failed: ${err.message}` },
        ],
        isError: true,
      };
    }
  }

  if (name === "list_voices") {
    const psScript = `
      Add-Type -AssemblyName System.Speech
      $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
      $synth.GetInstalledVoices() | ForEach-Object {
        $_.VoiceInfo | Select-Object Name, Gender, Age, Culture
      } | ConvertTo-Json
      $synth.Dispose()
    `;

    try {
      const { stdout } = await execFileAsync(
        "powershell",
        ["-NoProfile", "-Command", psScript],
        { timeout: 10000 }
      );
      return {
        content: [{ type: "text", text: stdout || "No voices found." }],
      };
    } catch (err) {
      return {
        content: [
          { type: "text", text: `❌ Failed to list voices: ${err.message}` },
        ],
        isError: true,
      };
    }
  }

  return {
    content: [{ type: "text", text: `Unknown tool: ${name}` }],
    isError: true,
  };
});

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
