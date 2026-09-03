---
name: secrets-hygiene
description: Run before committing, pushing, or sharing code externally — scans the files involved for hardcoded secrets such as API keys, tokens, or passwords, and blocks the action until they are removed or externalized.
version: 1.0.0
owner: ajay
status: shared
tags: [git, security]
---

# secrets-hygiene

Before committing, pushing, or sharing code, scan the files involved for
hardcoded secrets. Do not proceed while any remain.

1. **Scan.** Look for API keys, tokens, passwords, and private keys in the
   files about to leave the machine: high-entropy string literals, and known
   prefixes (`sk_live_`, `sk-`, `AKIA`, `ghp_`, `xoxb-`, `-----BEGIN`), and
   suspicious assignments (`password =`, `secret =`, `token =` with a literal).
   Check config files and test fixtures too — that's where secrets hide.
2. **Block.** If anything is found, STOP the commit/push/share. Name each file
   and line. Do not print the full secret value back — identify it by prefix
   and location.
3. **Fix, don't just delete.** Move the value to an environment variable or the
   project's secret store, reference it from code, and add the pattern to
   `.gitignore`/`.env.example` as appropriate. Warn that an already-committed
   secret must be rotated, not just removed — history retains it.
4. **Then proceed** with the original commit/push/share, and say what was
   externalized.

False-positive judgment: placeholder values (`sk_live_placeholder`, `changeme`,
`<your-key-here>`) and obviously fake test fixtures don't block — flag them
only if ambiguous.
