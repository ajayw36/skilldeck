# Writing and reading evals

A skill without evals is a skill you can't safely edit. Two kinds, testing two
independent failure modes:

## Trigger evals (`evals/triggers.yaml`) — does it fire?

The harness shows the model the FULL catalog of descriptions plus each prompt,
and records which skills it selects. Your skill is scored on recall (fired on
`should_trigger`) and precision (stayed quiet on `should_not_trigger`).

The `should_not_trigger` list must be **near-misses** — prompts in the same
territory that a sloppy description would catch. "Summarize this PDF" not firing
your deploy skill proves nothing; "deploy a preview build" not firing it proves
the boundary is real.

Adding a NEW skill can silently break an EXISTING skill's triggering (the
catalog changed). CI therefore runs trigger evals for changed skills plus their
tag-neighbors on PRs, and the full catalog nightly.

## Execution evals (`evals/cases/*.yaml`) — given that it fired, did it help?

Each case: a `task`, an optional `fixture` directory copied into a fresh
sandbox, programmatic `checks`, and a pairwise `judge` rubric. The harness runs
up to three arms, k reps each, with the real agent (`claude -p`):

- **baseline** — no skill. Comparison answers: does the skill help at all?
- **candidate** — your working-tree version.
- **incumbent** — the last committed version (only when it differs). Comparison
  answers: did this edit help?

Per rep: if exactly one arm passes all checks, it wins; otherwise the judge
compares the two transcripts (order randomized) against your rubric. Output is
win/loss/tie + a sign test — never an absolute score; absolute scores of skill
quality are noise.

Checks available: `transcript_mentions`, `command_matching` /
`no_command_matching` (regex over Bash commands the agent ran), `file_exists` /
`file_absent` (sandbox paths). Prefer checks over judge rubric wherever the
outcome is observable — checks don't drift with judge models.

**Every verified skill needs at least one adversarial case**: a fixture where
naively doing the task goes wrong (see deploy-preflight's `missing-env.yaml`).
Happy-path-only evals verify nothing.

## Generating evals

```sh
skill gen-evals my-skill --cases 3 --triggers 4
```

One model call generates new trigger prompts (merged into `triggers.yaml`) and
execution cases written as `evals/cases/gen-*.yaml` with **inline fixtures** —
a `files:` map materialized into the sandbox at run time, so generated cases
are self-contained. Invalid check kinds and duplicate names are dropped, and
every generated file carries a review header.

Bias warning: a model generating tests from a skill tends to generate tests
the skill passes. The generator is prompted toward outcome checks, adversarial
fixtures, and near-miss triggers, but read generated evals as *coverage*, not
proof — the baseline-vs-candidate arms are what keep the measurement honest,
since both arms face the same generated case.

## Running

```sh
skill evals my-skill --triggers-only   # seconds, cheap
skill evals my-skill --k 3             # PR-level
skill evals my-skill --k 10            # promotion-level
skill evals-report my-skill            # latest run summary
```

Results are JSONL under `results/` (gitignored). Cost note: execution evals are
the expensive part (arms × k × agent runs). If you must cut, cut PR-time
execution evals before trigger evals — a skill that fires wrongly is worse than
one that fires with mediocre advice.
