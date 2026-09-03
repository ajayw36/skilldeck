---
name: commit-style
description: Use when writing or amending a git commit message — enforces the team's format, imperative subject line of 50 characters or less and a body that explains why, not what.
version: 1.0.0
owner: ajay
status: shared
tags: [git, style]
---

# commit-style

When committing changes, the commit message must follow this format:

1. **Subject line**: imperative mood ("add", "fix", "remove" — not "added",
   "adds", or "adding"), 50 characters or fewer, no trailing period, capitalized
   first word. It should complete the sentence "If applied, this commit will …".
2. **Blank line** between subject and body.
3. **Body** (required for anything non-trivial): explain *why* the change was
   made and what alternatives were rejected — not a restatement of the diff.
   Wrap at 72 characters.
4. **One logical change per commit.** If the staged changes mix unrelated
   concerns (e.g. a bugfix and a formatting sweep), split them into separate
   commits rather than writing one message that covers both.

Never write vague subjects ("fix stuff", "updates", "wip"), and never let a
subject line describe less than the commit actually contains.
