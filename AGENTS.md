# Instructions for AI coding agents

This repository's instructions are in [CLAUDE.md](CLAUDE.md). They apply to every coding agent, whichever tool runs it.

Read, in order:
1. [CLAUDE.md](CLAUDE.md) — principle, commands, conventions
2. [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) — what to build
3. [PLAN.md](PLAN.md) — phases, verification iterations, exit criteria
4. [docs/PROGRESS.md](docs/PROGRESS.md) — current status

The verification roles in `.claude/agents/` (verifier, breaker, auditor, final-reviewer) are written for Claude Code sub-agents. With another tool, run the same roles as separate fresh sessions and give each only the inputs its file lists.
