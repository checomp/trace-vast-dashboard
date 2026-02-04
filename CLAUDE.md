## GitHub Account
**ALWAYS** use **checomp** for all projects:
- SSH: `git@github.com:checomp/trace-vast-dashboard.git`
- If the repo doesn't exist, create it. 

## library APIs or recent changes:
- Use Context7 MCP to fetch current documentation
- Prefer official docs over training knowledge
- Always verify version compatibility

## NEVER EVER DO

These rules are ABSOLUTE:

### NEVER Publish Sensitive Data
- NEVER publish passwords, API keys, tokens to git/npm/docker
- Before ANY commit: verify no secrets included

### NEVER Commit .env Files
- NEVER commit `.env` to git
- NEVER commit `logs` to git
- ALWAYS verify `.env` is in `.gitignore`

## New Project Setup

When creating ANY new project:

### Required Files
- `.env` — Environment variables (NEVER commit)
- `.env.example` — Template with placeholders
- `.gitignore` — Must include: .env, node_modules/, dist/
- `CLAUDE.md` — Project overview

### Required Structure
project/
├── src/
├── tests/
├── docs/
├── .claude/skills/
└── scripts/
└── logs/ (But this shouldn't be committed)
