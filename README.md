# Skills

Personal [Claude Code](https://claude.com/claude-code) skills by [@urunimi](https://github.com/urunimi).

## Install in Claude Code

Register this repository as a Claude Code plugin marketplace:

```
/plugin marketplace add urunimi/skills
```

Then run `/plugin install` and select the skills you want.

## Skills

### korean-polish

Korean translationese remover for Claude's Korean responses. Wraps a 2-pass refinement (draft → critique → final) as a skill so that Claude rewrites awkward English-flavored Korean (passive constructions, abstract-noun subjects, 1-to-1 lexical mappings like `govern → 지배`, `ensure → 보장`) into something a native speaker would actually write.

Based on findings from [Lost in Literalism (arXiv 2503.04369)](https://arxiv.org/html/2503.04369v1) and [Do Multilingual LLMs Think In English? (arXiv 2502.15603)](https://arxiv.org/html/2502.15603v1).

Background, design rationale, and a 1-pass vs. 2-pass branching rule: [blog.hovans.com/korean-polish-skill/](https://blog.hovans.com/korean-polish-skill/)

### refactor-check

Reviews changed code before a commit or PR. Alongside the usual consistency checks (duplication, naming and structural asymmetry, misplaced logic), it catches SOLID violations by **rule rather than definition** — reciting "a class should have one reason to change" never catches anything, but a grep for `isinstance` used to branch, an import buried inside a function to dodge a cycle, or a domain entity reaching for a factory does. Each rule ships with the principle it breaks and the direction of the fix, and the skill refuses "out of scope" and "follow-up PR" as resolutions.

Why definitions fail and what the rules are: [blog.hovans.com/solid-rules/](https://blog.hovans.com/solid-rules/)

## License

[Apache 2.0](./LICENSE)
