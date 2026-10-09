# CLAUDE.md — CrossCheck

## What this project is
CrossCheck is a mobile app (Expo React Native + TypeScript), a Python API (FastAPI), and an offline data/ML pipeline (Python). It helps Fairfax County students walk, bike, or scoot to school by lower-risk routes, report near-misses (sorted by AI), and produce a safety report for each school. It's a student's entry in the 2026 Congressional App Challenge (deadline: Monday, Oct 26, 2026, 12:00 PM ET).

## Source of truth
- `docs/DESIGN.md`: architecture, data, algorithms, API contract, and the build order (§11). Follow it.
- `docs/APP_FLOW.md`: every screen (S0–S19), states, and copy.
- If the code and the docs disagree, ask the student which is right, then update the doc in the same change.

## How we work (read before every task)
1. **One build step at a time.** The student names a step (for example, "Step 2.3"). Read that step in DESIGN.md §11 and the section it points to. Restate the goal and its "done when" in 2–3 lines, list your plan in 6 bullets or fewer, then wait for a go-ahead.
2. **★ steps are student-written.** Steps 1.7, 1.8, 2.3, 2.4, 4.2, and 5.2 are the student's core work. For these: explain the approach, point to the relevant docs and library functions, write tests and fixtures, review the student's code, and help debug. Don't write the core logic end to end. If the student asks for one small piece, write only that piece and explain it line by line. The Congressional App Challenge allows AI to support only parts of a project, requires disclosure, and expects the student to understand and explain all of it.
3. **Explain every change** in plain language after making it: what changed, why, and how to test it. Keep diffs small and focused on the current step.
4. **Log AI use.** After each step, add an entry to `AI_USAGE.md` (format below). If the file doesn't exist, create it starting with the design-docs entry.
5. **Don't expand scope.** Ideas outside DESIGN.md go in `docs/IDEAS.md`, not in code.
6. **Test before calling a step done.** Pipeline and server: `pytest -q` passes. Mobile: the step's "done when" works on the student's phone in Expo Go, and `npx tsc --noEmit` is clean.
7. **Teach as you go.** The student is new to some of these tools. When they need to do something themselves (run a command, scan a QR code, approve a firewall prompt), say exactly what to do and what they should see.

## Hard rules
- Never put API keys or secrets in mobile code or in git. Server secrets live only in `server/.env` (gitignored). Nothing secret goes in `EXPO_PUBLIC_` variables.
- Never store or log route origins (they may be near a student's home). Don't log request bodies.
- Strip EXIF from photos. Never store or show photos with faces or license plates, or photos whose AI sorting failed.
- UI copy says "lower-risk." Never "safe route" or "safest."
- Keep the S2 age question neutral (both options look the same and neither is pre-selected), and keep the under-13 stop in place.
- API coordinates are GeoJSON order `[lon, lat]`; react-native-maps wants `{latitude, longitude}`. Convert only with `toLatLng()`.
- Add Expo packages with `npx expo install`, not plain `npm install`, so versions match the SDK.
- All user-facing text goes in `mobile/src/copy/strings.ts`.
- Tunable numbers live in `pipeline/crosscheck_pipeline/config.py` and `server/app/config.py`, never inline.
- TypeScript strict mode; Python type hints. Don't add a dependency without saying why.

## This computer
Windows. The student runs commands in PowerShell (VS Code's default terminal). When you run commands yourself, use the syntax of the shell you're actually in: PowerShell as below, or in Git Bash activate with `source .venv/Scripts/activate`.

## Commands (PowerShell)
Pipeline:
```powershell
cd pipeline
py -3.12 -m venv .venv                             # first time only
.venv\Scripts\Activate.ps1
python -m crosscheck_pipeline.run_all              # all steps
python -m crosscheck_pipeline.run_all --from s05   # resume from a step
pytest -q
```

Server:
```powershell
cd server
py -3.12 -m venv .venv                             # first time only
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   # docs at http://localhost:8000/docs
pytest -q
python -m scripts.eval_ai                                   # AI golden-set accuracy
```

Mobile:
```powershell
cd mobile
npx expo start        # scan the QR code with Expo Go
npx tsc --noEmit      # type check
```

Windows gotchas:
- If PowerShell says running scripts is disabled, run this once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- The first time the server runs, Windows Firewall asks about Python. Allow it on private networks so the phone can reach the server.

## AI_USAGE.md format
Add one entry per step:
```markdown
### YYYY-MM-DD — Step X.Y: <step name>
- **Tool:** Claude Code
- **AI did:** (for example: scaffolded the FastAPI router; wrote routing tests; explained Dijkstra's algorithm)
- **I did:** (for example: wrote compare_routes() and the cost function; tuned ALPHA; fixed a lat/lon bug)
- **Files:** server/app/routing.py, server/tests/test_routing.py
```

The first entry (create it if `AI_USAGE.md` is missing; the student fills in the "I did" line):
```markdown
### 2026-10-07 — Design documents
- **Tool:** Claude (claude.ai)
- **AI did:** Fact-checked my video opening against news sources, summarized the challenge rules, and turned my app idea into docs/DESIGN.md, docs/APP_FLOW.md, and CLAUDE.md (architecture, data sources, algorithms, screen flow, and build order).
- **I did:** (my idea, features, and requirements; what I reviewed and changed in the plan)
```
