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

## License

[Apache 2.0](./LICENSE)
