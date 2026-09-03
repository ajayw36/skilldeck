"""Drive the real agent runtime headlessly. Never simulate the agent loop —
the point of every eval here is measuring the production agent's behavior."""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess

AGENT_CMD = os.environ.get("SKILLDECK_AGENT_CMD", "claude")
DEFAULT_TIMEOUT = 600


class AgentRunError(RuntimeError):
    pass


class Transcript:
    """Parsed stream-json transcript of one agent run."""

    def __init__(self, events: list[dict], result_text: str):
        self.events = events
        self.result_text = result_text

    def bash_commands(self) -> list[str]:
        cmds = []
        for e in self.events:
            for block in e.get("message", {}).get("content", []) or []:
                if isinstance(block, dict) and block.get("type") == "tool_use" \
                        and block.get("name") == "Bash":
                    cmds.append(str(block.get("input", {}).get("command", "")))
        return cmds

    def all_text(self) -> str:
        parts = [self.result_text]
        for e in self.events:
            for block in e.get("message", {}).get("content", []) or []:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, dict) and block.get("type") == "tool_use":
                    parts.append(json.dumps(block.get("input", {})))
        return "\n".join(parts)

    @classmethod
    def from_stream(cls, raw: str) -> "Transcript":
        events, result_text = [], ""
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            events.append(e)
            if e.get("type") == "result":
                result_text = e.get("result") or ""
        return cls(events, result_text)


def run_agent(prompt: str, cwd: pathlib.Path, transcript_path: pathlib.Path | None = None,
              max_turns: int = 25, timeout: int = DEFAULT_TIMEOUT) -> Transcript:
    """Run one sandboxed agent task and return its transcript.

    Sandboxing note: the agent runs with cwd pinned to the sandbox and
    acceptEdits permissions — good enough for trusted fixtures on a dev box.
    Run inside a container for untrusted skills.
    """
    cmd = [
        AGENT_CMD, "-p", prompt,
        "--output-format", "stream-json", "--verbose",
        "--max-turns", str(max_turns),
        "--permission-mode", "acceptEdits",
        "--allowedTools", "Bash Read Write Edit Glob Grep",
        # Isolate from the invoking user's personal config (global CLAUDE.md,
        # hooks, MCP servers) — evals must be reproducible across machines.
        "--setting-sources", "project",
        "--strict-mcp-config",
    ]
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(cwd)},
    )
    if transcript_path is not None:
        transcript_path.write_text(proc.stdout, encoding="utf-8")
    if proc.returncode != 0 and not proc.stdout.strip():
        raise AgentRunError(f"agent run failed (rc={proc.returncode}): {proc.stderr[-2000:]}")
    return Transcript.from_stream(proc.stdout)


def ask_json(prompt: str, timeout: int = 120) -> dict:
    """Single-turn, tool-free model call that must return a JSON object.

    Used for trigger selection and pairwise judging.
    """
    cmd = [AGENT_CMD, "-p", prompt, "--output-format", "json",
           "--max-turns", "1", "--disallowedTools", "*",
           "--setting-sources", "project", "--strict-mcp-config"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise AgentRunError(f"model call failed (rc={proc.returncode}): {proc.stderr[-2000:]}")
    try:
        outer = json.loads(proc.stdout)
        text = outer.get("result", "") if isinstance(outer, dict) else str(outer)
    except json.JSONDecodeError:
        text = proc.stdout
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise AgentRunError(f"model did not return JSON: {text[:500]!r}")
    return json.loads(match.group(0))
