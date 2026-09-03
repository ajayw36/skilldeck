"""Execution evals: three-arm pairwise comparison.

  baseline  — agent with no skill installed        (does the skill help at all?)
  candidate — agent with the working-tree skill    (the version under test)
  incumbent — agent with the last committed skill  (did this edit help?)

Each case runs k reps per arm in a fresh sandbox seeded from the fixture.
Per rep, the comparison is decided by programmatic checks first (if exactly one
arm passes all checks, it wins); the pairwise judge breaks the remaining ties.
Only win/loss/tie rates are reported — never absolute scores.
"""

from __future__ import annotations

import pathlib
import random
import shutil
import subprocess
import tempfile

import yaml

from ..manifest import Manifest
from .checks import run_checks
from .judge import judge_pair
from .runner import AgentRunError, Transcript, run_agent

ARMS = ("baseline", "candidate", "incumbent")


def load_case(path: pathlib.Path) -> dict:
    case = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not case.get("task"):
        raise ValueError(f"{path}: case needs a 'task'")
    case["_path"] = path
    case["name"] = path.stem
    return case


def incumbent_skill_text(repo_root: pathlib.Path, name: str) -> str | None:
    """The last committed SKILL.md, or None if new/uncommitted/unchanged repo state."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"HEAD:skills/{name}/SKILL.md"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _seed_sandbox(case: dict, skill_dir_src: pathlib.Path | None,
                  skill_md_override: str | None, skill_name: str,
                  scratch: pathlib.Path) -> pathlib.Path:
    sandbox = pathlib.Path(tempfile.mkdtemp(prefix="sd-", dir=scratch))
    fixture = case.get("fixture")
    if fixture:
        src = case["_path"].parent / fixture
        if not src.is_dir():
            raise FileNotFoundError(f"{case['_path']}: fixture dir not found: {src}")
        shutil.copytree(src, sandbox, dirs_exist_ok=True)
    for rel, content in (case.get("files") or {}).items():
        rel = str(rel)
        if rel.startswith(("/", "..")):
            raise ValueError(f"{case['_path']}: unsafe file path in case: {rel}")
        p = sandbox / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(str(content), encoding="utf-8")
        if rel.endswith(".sh"):
            p.chmod(0o755)
    if skill_dir_src is not None or skill_md_override is not None:
        dst = sandbox / ".claude" / "skills" / skill_name
        if skill_dir_src is not None:
            shutil.copytree(skill_dir_src, dst,
                            ignore=lambda d, names: [n for n in names if n in ("evals", "fixtures")])
        else:
            dst.mkdir(parents=True)
        if skill_md_override is not None:
            (dst / "SKILL.md").write_text(skill_md_override, encoding="utf-8")
    return sandbox


def run_case(repo_root: pathlib.Path, skill: Manifest, case: dict, k: int,
             scratch: pathlib.Path, seed: int = 0, log=print) -> list[dict]:
    """Run one case, k reps x available arms. Returns one result row per rep."""
    rng = random.Random(seed)
    incumbent_md = incumbent_skill_text(repo_root, skill.name)
    working_md = (skill.skill_dir / "SKILL.md").read_text(encoding="utf-8")
    arms: dict[str, tuple[pathlib.Path | None, str | None]] = {
        "baseline": (None, None),
        "candidate": (skill.skill_dir, None),
    }
    if incumbent_md is not None and incumbent_md != working_md:
        arms["incumbent"] = (skill.skill_dir, incumbent_md)

    rows = []
    for rep in range(k):
        transcripts: dict[str, Transcript | None] = {}
        checks_by_arm: dict[str, list] = {}
        for arm, (src, override) in arms.items():
            sandbox = _seed_sandbox(case, src, override, skill.name, scratch)
            tpath = scratch / f"{skill.name}.{case['name']}.{arm}.{rep}.jsonl"
            try:
                t = run_agent(case["task"], sandbox, transcript_path=tpath)
            except (AgentRunError, subprocess.TimeoutExpired) as e:
                log(f"  {case['name']} rep{rep} {arm}: agent run failed: {e}")
                t = None
            transcripts[arm] = t
            checks_by_arm[arm] = (
                [c.as_dict() for c in run_checks(case.get("checks") or [], t, sandbox)]
                if t is not None else []
            )

        for opponent in ("baseline", "incumbent"):
            if opponent not in arms:
                continue
            outcome = _decide(case, transcripts.get("candidate"), transcripts.get(opponent),
                              checks_by_arm.get("candidate", []), checks_by_arm.get(opponent, []),
                              rng)
            rows.append({
                "skill": skill.name, "kind": "execution", "case": case["name"],
                "rep": rep, "comparison": f"candidate-vs-{opponent}",
                "outcome": outcome["result"], "decided_by": outcome["decided_by"],
                "reason": outcome.get("reason", ""),
                "checks_candidate": checks_by_arm.get("candidate", []),
                f"checks_{opponent}": checks_by_arm.get(opponent, []),
            })
            log(f"  {case['name']} rep{rep} candidate-vs-{opponent}: "
                f"{outcome['result']} ({outcome['decided_by']})")
    return rows


def _decide(case: dict, cand: Transcript | None, opp: Transcript | None,
            cand_checks: list, opp_checks: list, rng: random.Random) -> dict:
    if cand is None and opp is None:
        return {"result": "tie", "decided_by": "both-arms-failed"}
    if cand is None:
        return {"result": "loss", "decided_by": "candidate-run-failed"}
    if opp is None:
        return {"result": "win", "decided_by": "opponent-run-failed"}

    cand_pass = all(c["passed"] for c in cand_checks)
    opp_pass = all(c["passed"] for c in opp_checks)
    if cand_pass != opp_pass:
        return {"result": "win" if cand_pass else "loss", "decided_by": "checks"}

    rubric = case.get("judge")
    if not rubric:
        return {"result": "tie", "decided_by": "checks-equal-no-judge"}
    verdict = judge_pair(case["task"], rubric, cand.all_text(), opp.all_text(), rng)
    result = {"left": "win", "right": "loss", "tie": "tie"}[verdict["winner"]]
    return {"result": result, "decided_by": "judge", "reason": verdict["reason"]}
