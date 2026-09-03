# Authoring a skill

Scaffold: `skill new my-skill`. Everything lives in `skills/my-skill/`.

## The description line is the product

The `description:` in the frontmatter is what the agent sees when deciding
whether to load your skill. It competes with every other description in the
catalog. Write it as a *when* statement with a boundary, not a *what* statement:

- Good: "Run before executing any production deploy — verifies env vars,
  migrations, and rollback readiness."
- Bad: "Helpful deployment utilities." (fires never, or fires for everything)

If `skill validate` warns that your description overlaps another skill's,
sharpen the boundary — two skills the agent can't pick between is worse than
either alone.

## The body

Write instructions for the agent, not documentation for humans. Number the
steps if order matters. State the failure behavior explicitly ("if X fails,
stop and report — do not proceed"). Put long reference material in
`references/` and mention it from the body — it loads lazily.

Optional helper scripts go in `scripts/`; reference them by relative path.

## Lifecycle

| status     | meaning | requirements |
|------------|---------|--------------|
| `draft`    | yours; may be broken | valid manifest |
| `shared`   | merged to main via PR | one reviewer |
| `verified` | passed the eval bar | ≥3 execution cases (incl. one adversarial), trigger evals with near-miss negatives, pairwise win over baseline at k=10 |

Publishing is a PR that adds/edits your `skills/<name>/` directory. CI runs
`skill validate`, `skill registry --check`, and evals for the changed skill.

## Versioning

Bump `version` (semver) on every behavioral edit. Git is the version store —
no per-version directories. `skill update` reinstalls when the version moves.
