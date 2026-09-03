---
name: incident-rollback
description: Use when rolling back or reverting an already-shipped production release — identifies the last good version, executes the rollback, and verifies recovery. Not for new deploys or forward fixes.
version: 1.0.0
owner: ajay
status: shared
tags: [deploy, incident]
---

# incident-rollback

When asked to roll back a production release, the goal is fastest safe recovery —
not diagnosis, not a forward fix. Follow this order:

1. **Identify versions.** Determine the currently deployed (bad) version and the
   last KNOWN-GOOD version from the repo's release records (release notes,
   deploy log, tags). Do not assume the previous version is good — check whether
   it was itself marked bad or rolled back; if so, go back further.
2. **Use the repo's rollback mechanism.** Prefer the project's own rollback
   tooling (a rollback script, a deploy tool's rollback command) over improvised
   git surgery. Reverting commits and redeploying is a last resort.
3. **State before executing.** Say which version you are rolling back to and why
   before running the command.
4. **Verify recovery.** After rolling back, confirm the service is on the target
   version and healthy (health check, version endpoint, or log tail).
5. **Preserve the evidence.** Do not delete or amend the bad release's artifacts
   or history — the postmortem needs them. Note the incident briefly (what was
   rolled back, from/to, when) in the repo's release records if they exist.

Do not attempt to diagnose or fix the underlying bug during the rollback unless
explicitly asked — recovery first, root cause after.
