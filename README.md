# Skills and agents

Personal [Claude Code](https://claude.com/claude-code) skills and agents by [@urunimi](https://github.com/urunimi).

## Install in Claude Code

Register this repository as a Claude Code plugin marketplace:

```
/plugin marketplace add urunimi/skills
```

Then run `/plugin install` and select the plugins you want.

## Skills

### korean-polish

Korean translationese remover for Claude's Korean responses. Wraps a 2-pass refinement (draft → critique → final) as a skill so that Claude rewrites awkward English-flavored Korean (passive constructions, abstract-noun subjects, 1-to-1 lexical mappings like `govern → 지배`, `ensure → 보장`) into something a native speaker would actually write.

Based on findings from [Lost in Literalism (arXiv 2503.04369)](https://arxiv.org/html/2503.04369v1) and [Do Multilingual LLMs Think In English? (arXiv 2502.15603)](https://arxiv.org/html/2502.15603v1).

Background, design rationale, and a 1-pass vs. 2-pass branching rule: [blog.hovans.com/korean-polish-skill/](https://blog.hovans.com/korean-polish-skill/)

### refactor-check

Reviews changed code before a commit or PR. Alongside the usual consistency checks (duplication, naming and structural asymmetry, misplaced logic), it catches SOLID violations by **rule rather than definition** — reciting "a class should have one reason to change" never catches anything, but a grep for `isinstance` used to branch, an import buried inside a function to dodge a cycle, or a domain entity reaching for a factory does. Each rule ships with the principle it breaks and the direction of the fix, and the skill refuses "out of scope" and "follow-up PR" as resolutions.

Why definitions fail and what the rules are: [blog.hovans.com/solid-rules/](https://blog.hovans.com/solid-rules/)

### pm-consult

Coordinates a Claude developer and a Codex PM in two Orca terminals. Codex owns product scope, UI/UX designs and acceptance criteria; Claude owns system design, implementation and tests. They review each other’s work at kickoff, design changes, before a PR and during PR review.

Requires Orca with both terminals open in the same worktree. Use the skill in both agents. It assumes Linear for issues and design documents, plus project-specific design and PR review tools. See [the skill](./skills/pm-consult/SKILL.md) for the workflow; adapt its default approval boundaries to your team.

## Agents

### ux-reviewer

A Claude Code subagent for planning reviews and real-browser UX reviews. It checks task flow, interaction cost, state and recovery, layout, language, and accessibility, then returns findings with evidence. It does not edit application code. Repeat reviews revisit open findings and affected screens.

Install after adding this marketplace:

```
/plugin install ux-reviewer@urunimi-skills
```

Ask Claude to delegate to the `ux-reviewer` agent and provide the task, screens, and acceptance criteria. For planning, explicitly request planning mode and supply a draft; for implementation, provide an app URL, safe test access, and an available browser tool. Planning estimates are kept separate from implementation measurements.

The [agent definition](./plugins/ux-reviewer/agents/ux-reviewer.md) is framework- and locale-independent. Browser tools are not bundled. Existing design rules, automated UX probes, PR gates, and screenshot hosting can be used through project-documented interfaces, but are optional. Without them, it produces a local report; it does not create a gate approval. External posting needs caller authorization. This is a Claude Code agent, not a portable `SKILL.md`.

## License

[Apache 2.0](./LICENSE)
