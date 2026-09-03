"""Eval results: JSONL on disk (results/ is gitignored — eval noise stays out
of main), summarized by `skill evals-report`."""

from __future__ import annotations

import collections
import datetime
import json
import pathlib

from .stats import summarize


def results_dir(repo_root: pathlib.Path, skill_name: str) -> pathlib.Path:
    d = repo_root / "results" / skill_name
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_run(repo_root: pathlib.Path, skill_name: str, rows: list[dict],
              meta: dict) -> pathlib.Path:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = results_dir(repo_root, skill_name) / f"{stamp}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"_meta": meta}) + "\n")
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return path


def latest_run(repo_root: pathlib.Path, skill_name: str) -> pathlib.Path | None:
    d = repo_root / "results" / skill_name
    if not d.is_dir():
        return None
    runs = sorted(d.glob("*.jsonl"))
    return runs[-1] if runs else None


def report(path: pathlib.Path) -> str:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    meta = rows[0].get("_meta", {}) if rows and "_meta" in rows[0] else {}
    rows = [r for r in rows if "_meta" not in r]
    lines = [f"run: {path.name}   meta: {json.dumps(meta)}"]

    trig = [r for r in rows if r.get("kind") == "triggers"]
    for t in trig:
        lines.append(
            f"triggers: recall={_fmt(t['recall'])} precision={_fmt(t['precision'])} "
            f"(tp={t['tp']} fn={t['fn']} fp={t['fp']} tn={t['tn']})"
        )
        for r in t["rows"]:
            if not r["correct"]:
                kind = "MISS" if r["expected"] else "FALSE-FIRE"
                lines.append(f"  {kind}: {r['prompt']!r}")

    execs = [r for r in rows if r.get("kind") == "execution"]
    by_cmp = collections.defaultdict(lambda: collections.Counter())
    for r in execs:
        by_cmp[r["comparison"]][r["outcome"]] += 1
    for cmp_name, counts in sorted(by_cmp.items()):
        lines.append(f"{cmp_name}: "
                     + summarize(counts["win"], counts["loss"], counts["tie"]))
    return "\n".join(lines)


def _fmt(v) -> str:
    return "n/a" if v is None else f"{v:.2f}"
