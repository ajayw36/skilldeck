---
name: deploy-preflight
description: Run before executing any production deploy — verifies required env vars, pending migrations, and rollback readiness before any deploy command is run.
version: 1.0.0
owner: ajay
status: verified
tags: [deploy, ci]
---

# deploy-preflight

Before running ANY production deploy command, complete this preflight checklist.
Do not execute the deploy until every item passes; if an item fails, stop, report
it, and propose the fix instead of deploying.

1. **Environment variables.** Find the service's required env vars (check
   `.env.example`, the deploy script itself, and CI config). Verify each one is
   set in the deploy environment. A deploy script that reads an unset secret is
   the most common cause of a broken prod deploy.
2. **Migrations.** Check for unapplied database migrations. If any exist,
   confirm the deploy process applies them (or apply them first, per the repo's
   convention) — never deploy code that expects a schema that isn't there yet.
3. **Rollback readiness.** Identify the current deployed version (git tag,
   release file, or deploy log) and state the exact rollback command before
   deploying. If you can't determine how to roll back, that's a preflight
   failure.
4. **Dry run when available.** If the deploy tooling supports a dry-run or
   plan mode, run it and review the output before the real deploy.

Only after all four pass: run the deploy, then verify it (health check, smoke
test, or log tail) and report what you verified.
