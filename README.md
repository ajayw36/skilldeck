# skilldeck

Git-native agent skill management for a team: author skills as files, share them
through pull requests, install them with one command, and hold them to an eval
bar before they're trusted.

## Layout

```
skills/<name>/SKILL.md        # the skill: YAML frontmatter manifest + markdown body
skills/<name>/evals/          # co-located evals (triggers.yaml + cases/*.yaml)
registry.json                 # generated index — never hand-edit; run `skill registry`
results/                      # eval runs as JSONL (gitignored — yours alone)
tools/skilldeck/              # the `skill` CLI and eval harness
docs/                         # authoring + eval guides
```

The `skills/` directory is **flat** — no categories, no nesting. Tags in the
manifest are the taxonomy.

## Setup

```sh
python3 -m venv .venv && .venv/bin/pip install -e .
alias skill=$PWD/.venv/bin/skill      # add to ~/.zshrc to keep it
```

Evals run through the `claude` CLI using your existing Claude Code auth — no
API key needed locally. (CI needs an `ANTHROPIC_API_KEY` repo secret.)

## Commands

```sh
skill list                    # browse the catalog
skill web                     # local dashboard: tiles, run history, judge reasons
skill install <name>          # copy into ~/.claude/skills (+ lockfile pin)
skill update                  # reinstall anything whose repo version moved

skill new <name>              # scaffold a skill + eval templates
skill validate                # lint manifests + eval requirements (CI gate)
skill registry                # regenerate registry.json (commit it)

skill gen-evals <name>        # model-generated trigger prompts + cases + fixtures
skill evals <name>            # trigger + execution evals (see below)
skill evals-report <name>     # summary of the latest run
```

## Evals

Two independent measurements, because skills fail two independent ways:

**Trigger evals** — shown the full catalog of descriptions, does the model load
this skill for prompts that should fire it, and stay quiet on near-misses?
Scored as recall / precision; failures print the exact prompt.

**Execution evals** — the real agent (`claude -p`) runs each case in a fresh
sandbox, in up to three arms: no skill (**baseline**), your working tree
(**candidate**), and the last committed version (**incumbent**). Programmatic
checks decide first; a pairwise LLM judge breaks ties. Reported as **net lift**
— the fraction of comparisons the skill improved, minus the fraction it
degraded — with W/L/T counts and a sign test:

```
candidate-vs-baseline: +44% net lift (5W / 1L / 3T over 9 comparisons, sign test p=0.219)
```

```sh
skill evals my-skill --triggers-only          # seconds, cheap
skill evals my-skill --k 3                    # PR-level depth
skill evals my-skill --k 10                   # promotion-level
skill evals my-skill --execution-only --case <stem> --k 1   # one case, cheapest
skill evals my-skill --model opus             # override the model (default: haiku)
```

All harness calls run on **haiku** by default and the model is recorded in each
run's meta — only compare numbers across runs on the same model. Cases support
inline `files:` fixtures and a `setup:` shell hook (git init, local remotes);
`skill gen-evals` generates all of it, marked for review. See
`docs/eval-guide.md` for the full case format and the honesty caveats.

## Skill lifecycle

| status     | meaning | requirements |
|------------|---------|--------------|
| `draft`    | yours; may be broken | valid manifest |
| `shared`   | merged to main via PR | one reviewer |
| `verified` | passed the eval bar | ≥3 execution cases (incl. one adversarial), trigger evals with near-miss negatives, pairwise win over baseline at k=10 |

Publishing is a PR touching `skills/<name>/`. CI runs `skill validate`,
`skill registry --check`, and evals for changed skills (`.github/workflows/`).

## Team setup

Push this repo to a shared private remote; teammates clone it and run Setup
above. Consuming teammates' skills is `git pull && skill update`. The
description line in each manifest is the trigger — the whole catalog competes
for the agent's attention, so `skill validate` warns on overlapping
descriptions and nightly CI reruns trigger evals across the full catalog.

See `docs/authoring-guide.md` to write your first skill.
