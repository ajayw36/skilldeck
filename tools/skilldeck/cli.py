"""The `skill` CLI."""

from __future__ import annotations

import argparse
import pathlib
import sys
import tempfile

from . import install as install_mod
from . import registry as registry_mod
from .manifest import ManifestError, load_all, parse_skill_md, validate_repo

NEW_SKILL_TEMPLATE = """---
name: {name}
description: <one sentence saying exactly WHEN an agent should load this — this line IS the trigger>
version: 0.1.0
owner: {owner}
status: draft
tags: []
---

# {name}

<instructions for the agent>
"""

NEW_TRIGGERS_TEMPLATE = """should_trigger:
  - "<a realistic user prompt that should fire this skill>"
should_not_trigger:
  - "<a NEAR-MISS: a prompt in the same territory that should NOT fire it>"
"""

NEW_CASE_TEMPLATE = """task: "<the task given to the agent>"
# fixture: fixtures/example/          # optional dir copied into the sandbox
checks:
  - transcript_mentions: "<string that must appear>"
  # - no_command_matching: "rm -rf"   # regex over Bash commands the agent ran
  # - command_matching: "pytest"
  # - file_exists: "out/report.md"
  # - file_absent: "secrets.txt"
judge: |
  <what makes one transcript better than another, for the pairwise judge>
"""


def find_repo_root(start: pathlib.Path | None = None) -> pathlib.Path:
    p = (start or pathlib.Path.cwd()).resolve()
    for candidate in (p, *p.parents):
        if (candidate / "skills").is_dir() and (candidate / "pyproject.toml").is_file():
            return candidate
    sys.exit("error: not inside a skilldeck repo (no skills/ + pyproject.toml found upward)")


def cmd_new(args) -> int:
    root = find_repo_root()
    d = root / "skills" / args.name
    if d.exists():
        sys.exit(f"error: {d} already exists")
    (d / "evals" / "cases").mkdir(parents=True)
    import getpass
    (d / "SKILL.md").write_text(
        NEW_SKILL_TEMPLATE.format(name=args.name, owner=getpass.getuser()), encoding="utf-8")
    (d / "evals" / "triggers.yaml").write_text(NEW_TRIGGERS_TEMPLATE, encoding="utf-8")
    (d / "evals" / "cases" / "basic.yaml").write_text(NEW_CASE_TEMPLATE, encoding="utf-8")
    print(f"scaffolded {d}\nnext: edit SKILL.md (the description line is the trigger — "
          "write it carefully), fill in the evals, then `skill validate`")
    return 0


def cmd_validate(args) -> int:
    root = find_repo_root()
    problems = validate_repo(root)
    if problems:
        for p in problems:
            print(f"FAIL {p}")
        return 1
    n = len(load_all(root))
    print(f"ok: {n} skill(s) valid")
    if not registry_mod.is_current(root):
        print("note: registry.json is stale — run `skill registry`")
    return 0


def cmd_registry(args) -> int:
    root = find_repo_root()
    if args.check:
        if registry_mod.is_current(root):
            print("registry.json is current")
            return 0
        print("FAIL registry.json is stale — run `skill registry` and commit it")
        return 1
    path = registry_mod.write(root)
    print(f"wrote {path}")
    return 0


def cmd_list(args) -> int:
    root = find_repo_root()
    for m in load_all(root):
        if args.tag and args.tag not in m.tags:
            continue
        evals = f"{len(m.execution_cases())} cases" + \
                ("" if m.triggers_file() else ", NO trigger evals")
        print(f"{m.name:24} {m.version:8} {m.status:9} [{', '.join(m.tags)}] "
              f"({evals})  {m.description}")
    return 0


def cmd_install(args) -> int:
    root = find_repo_root()
    target = pathlib.Path(args.target).expanduser() if args.target else install_mod.DEFAULT_TARGET
    try:
        print(install_mod.install(root, args.name, target))
    except ManifestError as e:
        sys.exit(f"error: {e}")
    return 0


def cmd_update(args) -> int:
    root = find_repo_root()
    target = pathlib.Path(args.target).expanduser() if args.target else install_mod.DEFAULT_TARGET
    for msg in install_mod.update(root, target, args.name):
        print(msg)
    return 0


def cmd_evals(args) -> int:
    root = find_repo_root()
    skill_md = root / "skills" / args.name / "SKILL.md"
    if not skill_md.is_file():
        sys.exit(f"error: no such skill: {args.name}")
    skill = parse_skill_md(skill_md)

    from .evals import results as results_mod
    rows: list[dict] = []
    meta = {"skill": skill.name, "version": skill.version, "k": args.k}

    if not args.execution_only:
        from .evals.triggers import run_trigger_evals
        print(f"trigger evals for {skill.name} (catalog of {len(load_all(root))} skills)...")
        trig = run_trigger_evals(root, skill)
        rows.append(trig)
        print(f"  recall={trig['recall']} precision={trig['precision']}")

    if not args.triggers_only:
        from .evals.execution import load_case, run_case
        cases = skill.execution_cases()
        if args.case:
            cases = [c for c in cases if c.stem == args.case]
            if not cases:
                sys.exit(f"error: no case named {args.case!r}")
        if not cases:
            print(f"no execution cases in {skill.evals_dir}/cases/")
        scratch = pathlib.Path(tempfile.mkdtemp(prefix=f"skilldeck-{skill.name}-"))
        print(f"execution evals: {len(cases)} case(s), k={args.k} (sandboxes in {scratch})")
        for cpath in cases:
            case = load_case(cpath)
            rows.extend(run_case(root, skill, case, args.k, scratch))

    path = results_mod.write_run(root, skill.name, rows, meta)
    print(f"\nresults -> {path}\n")
    print(results_mod.report(path))
    return 0


def cmd_gen_evals(args) -> int:
    root = find_repo_root()
    skill_md = root / "skills" / args.name / "SKILL.md"
    if not skill_md.is_file():
        sys.exit(f"error: no such skill: {args.name}")
    skill = parse_skill_md(skill_md)
    from .evals.generate import generate
    print(f"generating {args.cases} case(s) and {args.triggers}+{args.triggers} trigger "
          f"prompts for {skill.name} (one model call, may take a minute)...")
    summary = generate(root, skill, n_cases=args.cases, n_triggers=args.triggers)
    print(f"triggers added: {summary['triggers_added']} (merged into evals/triggers.yaml)")
    for p in summary["cases_written"]:
        print(f"case written:   {p}")
    for d in summary["dropped"]:
        print(f"dropped:        {d}")
    print("\ngenerated evals are marked with a review header — read them before trusting; "
          "a model generating tests from a skill tends to generate tests the skill passes.\n"
          f"next: skill evals {skill.name} --triggers-only, then --execution-only --k 1")
    return 0


def cmd_evals_report(args) -> int:
    root = find_repo_root()
    from .evals import results as results_mod
    path = results_mod.latest_run(root, args.name)
    if path is None:
        sys.exit(f"error: no eval runs found for {args.name}")
    print(results_mod.report(path))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="skill", description="git-native agent skill management")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("new", help="scaffold a new skill with eval templates")
    sp.add_argument("name")
    sp.set_defaults(fn=cmd_new)

    sp = sub.add_parser("validate", help="lint all manifests and eval requirements")
    sp.set_defaults(fn=cmd_validate)

    sp = sub.add_parser("registry", help="regenerate registry.json")
    sp.add_argument("--check", action="store_true", help="fail if registry.json is stale")
    sp.set_defaults(fn=cmd_registry)

    sp = sub.add_parser("list", help="list skills in the catalog")
    sp.add_argument("--tag")
    sp.set_defaults(fn=cmd_list)

    sp = sub.add_parser("install", help="copy a skill into your agent config (with lockfile)")
    sp.add_argument("name")
    sp.add_argument("--target", help=f"install dir (default {install_mod.DEFAULT_TARGET})")
    sp.set_defaults(fn=cmd_install)

    sp = sub.add_parser("update", help="reinstall locked skills whose repo version moved")
    sp.add_argument("name", nargs="?")
    sp.add_argument("--target")
    sp.set_defaults(fn=cmd_update)

    sp = sub.add_parser("evals", help="run trigger + execution evals for a skill")
    sp.add_argument("name")
    sp.add_argument("--k", type=int, default=3, help="reps per arm (default 3; use 10 for promotion)")
    sp.add_argument("--triggers-only", action="store_true")
    sp.add_argument("--execution-only", action="store_true")
    sp.add_argument("--case", help="run only this execution case (by filename stem)")
    sp.set_defaults(fn=cmd_evals)

    sp = sub.add_parser("gen-evals", help="generate trigger prompts and execution cases with the model")
    sp.add_argument("name")
    sp.add_argument("--cases", type=int, default=3, help="execution cases to generate (default 3)")
    sp.add_argument("--triggers", type=int, default=4, help="prompts per trigger list (default 4)")
    sp.set_defaults(fn=cmd_gen_evals)

    sp = sub.add_parser("evals-report", help="summarize the latest eval run for a skill")
    sp.add_argument("name")
    sp.set_defaults(fn=cmd_evals_report)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
