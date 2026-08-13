---
name: refactor-check
description: |
  Analyze newly added/modified code against the existing codebase for SOLID violations and consistency issues.
  Use when: (1) New code was just added or modified, (2) User asks to check code consistency,
  (3) User says "refactor check", "consistency check", or "코드 정리",
  (4) After implementing a feature, before committing or opening a PR.
---

# Refactor Check

Analyze changed code in the context of the surrounding codebase. Find SOLID violations,
duplication, naming inconsistencies, and structural asymmetry, then fix them.

## What This Skill Catches

| Category | Description | Example |
|----------|-------------|---------|
| **Duplication** | New code duplicates existing logic | `delete_user` re-implements the permission check already in `update_user` |
| **Naming asymmetry** | Related methods use inconsistent naming | `create_order` vs `remove_item` |
| **Structural asymmetry** | Paired operations don't follow the same pattern | `create_X` validates, `update_X` skips it |
| **Misplaced logic** | Code belongs in a different layer | Business rule enforced in the router, not the service |
| **Unnecessary divergence** | Similar methods differ without reason | Two exports using different date formats |

## SOLID: catch it by rule, not by definition

Reciting the five definitions does not surface violations — whoever wrote the code already knew
them and shipped the violation anyway. Check the **added lines** against these rules instead. Each
one is mechanically checkable and has a known cure. A hit means "stop and find the cause", not
"guilty".

| Rule — what to look for in added lines | Principle | Cure |
|---|---|---|
| `isinstance` / `issubclass` / `type(x) ==` used to branch | OCP, LSP | Let the implementation answer, or split the registry so that registration *is* the answer |
| Import placed inside a function to dodge an import cycle | DIP | The arrow points the wrong way — invert it instead of hiding it |
| A domain entity or ORM model calling an adapter, registry, or factory | DIP, SRP | Inject the abstraction; the entity must not reach outward |
| Deployment data (keys, URLs, paths) hardcoded beside a dispatch table | DIP, OCP | Dispatch on one selector that comes from config |
| The same fact written into two tables | OCP | Make registration the single source; a missing entry is the negative answer |

Fix what you find **in the current change**. "Out of scope", "follow-up PR", and "filed a ticket"
are not resolutions — split the commits if the refactor grows, but keep it in the same PR.

## Workflow

### Step 1: Identify Changes

Spawn an **Explore sub-agent** to:

1. Run `git diff` (staged + unstaged) or `git diff origin/main...HEAD` to identify changed hunks
2. For each changed file, read the **full file** (not just the diff) to understand context
3. Identify all **new or modified functions/methods/classes**
4. Check added lines against the rules above and record every `file:line` hit

### Step 2: Analyze Relationships

For each changed function, spawn an **Explore sub-agent** to:

1. **Find siblings**: other methods doing similar work (same prefix, parameters, return types)
2. **Find callers**: all call sites of the changed function and its siblings
3. **Find shared logic**: code blocks appearing in both the new and the existing code
4. **Check naming conventions**: compare naming patterns across the module

### Step 3: Report

Group findings by file. For each one give what it is, where it is, and the concrete fix.

```
## file_path

### SOLID — DIP
- `Channel.supports_read_check` (line X) imports the notifier factory inside the method
  - The function-local import exists only to dodge a cycle → the dependency points the wrong way
  - Fix: inject the notifier so the entity answers from what it already holds

### Duplication
- `new_method` (line X) duplicates `existing_method` (line Y)
  - Fix: extract a shared method, or unify them with a parameter
```

If nothing is found, say so plainly: "No SOLID or consistency issues detected."

### Step 4: Fix

1. SOLID violations first — they shape everything else
2. Naming asymmetry next (least risky)
3. Extract shared logic / merge duplicates
4. Update all callers and tests, then run the tests

When the change is meant to be a pure refactor, **prove behaviour is unchanged**: run the old and
the new code over the same real input and diff the outputs.

## Guidelines

- Focus on the **changed code and its immediate neighbors** — don't audit the entire codebase
- A rule hit may be a false positive; justify it in one line or fix it, never skip it silently
- Prefer unifying over splitting: one flexible method > two rigid ones (unless type safety suffers)
- Respect intentional differences — if two methods genuinely need different logic, leave them
- When naming, prefer the convention already dominant in the codebase
- Always identify all callers before suggesting a rename
