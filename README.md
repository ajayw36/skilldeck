# skilldeck

Git-native agent skill management for a team: author skills as files, share them
through pull requests, install them with one command, and hold them to an eval bar
before they're trusted.

## Layout

```
skills/<name>/SKILL.md        # the skill: YAML frontmatter manifest + markdown body
skills/<name>/evals/          # co-located evals (trigger + execution cases)
registry.json                 # generated index — never hand-edit; run `skill registry`
tools/skilldeck/              # the `skill` CLI and eval harness
docs/                         # authoring + eval guides
```

The `skills/` directory is **flat** — no categories, no nesting. Tags in the
manifest are the taxonomy.

## Quickstart

```sh
python3 -m venv .venv && .venv/bin/pip install -e .
alias skill=$PWD/.venv/bin/skill

skill list                    # browse the catalog
skill install deploy-preflight   # copy into ~/.claude/skills + lockfile
skill new my-skill            # scaffold a new skill + eval templates
skill validate                # lint all manifests (CI runs this on every PR)
skill registry                # regenerate registry.json (CI checks it's current)
```

## Skill lifecycle

`draft` → `shared` (published via PR, one reviewer) → `verified` (passed the eval
bar: ≥3 execution cases, trigger evals with near-miss negatives, and a pairwise
eval win over baseline).

## Evals

```sh
skill evals deploy-preflight --triggers-only     # cheap: does it fire when it should?
skill evals deploy-preflight --k 3               # execution: baseline vs candidate vs incumbent
skill evals-report deploy-preflight              # summarize the latest run
```

Execution evals run the real agent (`claude -p`) headlessly in a sandbox seeded
from each case's fixture, in up to three arms — no skill (baseline), your
working-tree version (candidate), and the last committed version (incumbent) —
then decide each rep by programmatic checks first and a pairwise LLM judge only
for what checks can't express. Results land in `results/` as JSONL (gitignored).

See `docs/authoring-guide.md` and `docs/eval-guide.md`.
