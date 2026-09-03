"""Pairwise LLM judge. Never scores a transcript in isolation — pairwise
comparison with randomized ordering is far more stable across judge models."""

from __future__ import annotations

import random

from .runner import ask_json

TRANSCRIPT_TAIL = 6000  # chars of each transcript shown to the judge

PROMPT = """You are judging two AI agent transcripts for the same task. Decide which one
better satisfies the rubric. Be strict; "tie" is a valid answer when neither is clearly better.

TASK GIVEN TO BOTH AGENTS:
{task}

RUBRIC:
{rubric}

TRANSCRIPT A (tail):
{a}

TRANSCRIPT B (tail):
{b}

Respond with ONLY a JSON object: {{"winner": "A" | "B" | "tie", "reason": "<one sentence>"}}
"""


def judge_pair(task: str, rubric: str, left_text: str, right_text: str,
               rng: random.Random) -> dict:
    """Compare two transcripts. Returns {"winner": "left"|"right"|"tie", "reason": ...}.

    left/right are the caller's labels; A/B assignment is randomized here so the
    judge can't develop a position bias.
    """
    swap = rng.random() < 0.5
    a, b = (right_text, left_text) if swap else (left_text, right_text)
    verdict = ask_json(PROMPT.format(
        task=task, rubric=rubric,
        a=a[-TRANSCRIPT_TAIL:], b=b[-TRANSCRIPT_TAIL:],
    ))
    winner = str(verdict.get("winner", "tie")).strip().upper()
    if winner not in ("A", "B"):
        mapped = "tie"
    elif (winner == "A") != swap:
        mapped = "left"
    else:
        mapped = "right"
    return {"winner": mapped, "reason": str(verdict.get("reason", "")), "swapped": swap}
