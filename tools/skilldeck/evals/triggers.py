"""Trigger evals: given the FULL catalog of skill descriptions (the realistic
condition — skills compete for attention), does the agent load this skill for
prompts that should fire it, and leave it alone for near-misses?"""

from __future__ import annotations

import pathlib

import yaml

from ..manifest import Manifest, load_all
from ..registry import catalog_lines
from .runner import AgentRunError, ask_json

SELECTION_PROMPT = """You are an AI coding agent deciding which skills to load for a user request.
Below is your full skill catalog. Select every skill whose description says it should be used
for this request — and no others. Selecting nothing is often correct.

SKILL CATALOG:
{catalog}

USER REQUEST:
{prompt}

Respond with ONLY a JSON object: {{"selected": ["skill-name", ...]}}
"""


def run_trigger_evals(repo_root: pathlib.Path, skill: Manifest) -> dict:
    tf = skill.triggers_file()
    if tf is None:
        raise FileNotFoundError(f"{skill.name}: no evals/triggers.yaml")
    spec = yaml.safe_load(tf.read_text(encoding="utf-8")) or {}
    should = list(spec.get("should_trigger") or [])
    should_not = list(spec.get("should_not_trigger") or [])
    catalog = catalog_lines(load_all(repo_root))

    rows = []
    for prompt, expected in [(p, True) for p in should] + [(p, False) for p in should_not]:
        try:
            verdict = ask_json(SELECTION_PROMPT.format(catalog=catalog, prompt=prompt))
            selected = [str(s) for s in verdict.get("selected", [])]
            fired = skill.name in selected
            rows.append({"prompt": prompt, "expected": expected, "fired": fired,
                         "selected": selected, "correct": fired == expected})
        except AgentRunError as e:
            rows.append({"prompt": prompt, "expected": expected, "fired": None,
                         "selected": [], "correct": False, "error": str(e)})

    tp = sum(1 for r in rows if r["expected"] and r["fired"])
    fn = sum(1 for r in rows if r["expected"] and not r["fired"])
    fp = sum(1 for r in rows if not r["expected"] and r["fired"])
    tn = sum(1 for r in rows if not r["expected"] and r["fired"] is False)
    recall = tp / (tp + fn) if (tp + fn) else None
    precision = tp / (tp + fp) if (tp + fp) else None
    return {"skill": skill.name, "kind": "triggers", "rows": rows,
            "recall": recall, "precision": precision,
            "tp": tp, "fn": fn, "fp": fp, "tn": tn}
