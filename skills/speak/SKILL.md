---
name: speak
description: "Speak text aloud using Windows text-to-speech. Use this skill when the user asks you to say something, read something aloud, or speak your response."
---

When this skill is invoked, use the `speak` MCP tool to read text aloud through the system speakers.

WHEN to activate:
- The user says "say this", "read this aloud", "speak", "tell me out loud", or similar
- The user asks you to voice your response

HOW to use:
1. Compose your response text (plain text, no markdown formatting)
2. Call the `speak` tool with the text and optionally a speech rate
3. Confirm to the user that the text was spoken

GUIDELINES:
- Strip markdown formatting (bold, links, code blocks) before speaking
- Keep spoken text concise — summarize long responses for speech
- Default speech rate is 0 (normal). Range is -10 (slowest) to 10 (fastest)
- You can speak partial responses while still typing the full answer
