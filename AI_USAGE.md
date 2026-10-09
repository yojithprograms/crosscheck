# AI Usage Log

A running record of how AI helped build CrossCheck, for the Congressional App Challenge disclosure.

### 2026-10-07 — Design documents
- **Tool:** Claude (claude.ai)
- **AI did:** Fact-checked my video opening against news sources, summarized the challenge rules, and turned my app idea into docs/DESIGN.md, docs/APP_FLOW.md, and CLAUDE.md (architecture, data sources, algorithms, screen flow, and build order).
- **I did:** (my idea, features, and requirements; what I reviewed and changed in the plan)

### 2026-10-08 — Step 0.2: Repo skeleton
- **Tool:** Claude Code
- **AI did:** Created the folder layout from DESIGN.md §4, `.gitignore`, a README stub, empty `docs/MODEL_NOTES.md` and `docs/IDEAS.md`, `server/.env.example` (placeholder values only), and this log.
- **I did:** (created the GitHub repo and pushed the first commit)
- **Files:** .gitignore, README.md, AI_USAGE.md, server/.env.example, docs/MODEL_NOTES.md, docs/IDEAS.md, folder skeleton with .gitkeep files

### 2026-10-08 — Step 0.3: Python environments
- **Tool:** Claude Code
- **AI did:** Created `pipeline/.venv` and `server/.venv` with Python 3.12, installed the packages listed in DESIGN.md §11, ran the import check, and pinned versions with `pip freeze`.
- **I did:** (reviewed the package lists; activated the environments in my own terminal)
- **Files:** pipeline/requirements.txt, server/requirements.txt
