# Agent Rules

Priority: task README and exam rules > user instructions > this file. If they conflict, follow the higher one and say so in one line.
Reply to the user in Korean. Keep all work documents in `work/` (TASK, DECISIONS, HANDOFF, VERIFY) and write them in Korean.

## Hard rules (never break)
1. NEVER use Computer Use (screen automation) at any stage, including automating the built-in Browser. Ask BEFORE using any browser automation tool (e.g. Playwright).
2. NEVER git push, send files outside, print keys/tokens/passwords, touch exam platform or proctoring processes, or add dependencies nobody asked for.
3. NO code before the user confirms work/TASK.md.
4. NEVER claim something works unless a test run passed. Mark what you could not run as "미검증".
5. When t.py prints `[경고]` or the same fix failed twice: STOP. Report 2 cause hypotheses and how to check each, then wait.
6. If your implementation differs from work/TASK.md, say so. Never adjust silently.

## Shortcuts (when the user types exactly these, read the card and follow it)
- `킥오프` : `.kit/prompts/1_kickoff.md`
- `C3 진행` (any criterion id) : `.kit/prompts/2_build.md` for that criterion
- `리뷰` : `.kit/prompts/3_review.md`
- `핸드오프` : `.kit/prompts/4_handoff.md`
- `제출점검` : `.kit/prompts/5_presubmit.md`
- `수동확인 C3` : `.kit/prompts/6_manual.md` for that criterion
- `분리` : `.kit/prompts/7_split.md`

## Read when relevant (once per session)
- Web pages, APIs, frontend: `.kit/docs/web.md`
- CSV, DB, data import: `.kit/docs/db.md`
- Login, passwords, env vars: `.kit/docs/auth.md`

## Workflow
1. Read the task README. For unfamiliar files, data or folders run `python3 .kit/tools/peek.py <path>` and open only what you need.
2. Fill work/TASK.md: requirements with source, every constraint category ("없음" if none), assumptions, small done criteria (5 to 10 min each) with a verification method. If the task names required documents or files, write there instead of duplicating. If parts can be built in parallel, fix the interface between them first. C0 is always a thin end-to-end version on fake data.
3. One criterion at a time (after `분리`, only your track's criteria and files; commit by path): plan in 3 lines, show a short skeleton (names, inputs/outputs, data flow), wait for confirmation, then implement.
4. Test only that criterion: `python3 .kit/tools/t.py --note "C3" -- python3 -m pytest -q -k C3_` (name tests `test_C3_...`). Full suite (`python3 .kit/tools/t.py`) every 2 to 3 criteria.
5. When it passes: local commit, mark 완료 in TASK.md, explain in 3 lines (what changed, why vs the alternative, where it could break), STOP. The user writes DECISIONS.md. No git repo: ask before `git init`.
6. If requirements change, update TASK.md and its change log BEFORE code.
7. After each completed criterion, update only the "현재 상태" section of work/HANDOFF.md (3 lines max). Rewrite the whole file only on `핸드오프`. A new session reads only HANDOFF.md, TASK.md, DECISIONS.md.

## Token discipline
- Before fixing a failure, state its cause in one line. If unknown, investigate first. No guess-edits.
- `[SAME]` from t.py: nothing changed, do not rerun.
- Long-output commands (install, build, scripts): `python3 .kit/tools/q.py -- <cmd>`. Install only if `python3 .kit/tools/peek.py --env` shows it missing, with `pip install -q`.
- Never dump large files. Use peek, `rg -n`, `sed -n 'A,Bp'`. Do not reread unchanged files.
- Do not start servers yourself; give the command to the user.
- Short replies: files changed, test result, remaining risk. No pasted code or long output.

## Minimal change
Build only what TASK.md asks. Reuse existing code, then the standard library, then installed packages. No unrequested features, abstractions, options or dependencies. Fix the callers and tests your change breaks. Never cut input validation, data-loss protection or security. Full rules: `.kit/docs/minimal.md` (adapted from Ponytail, MIT).

End every reply with one line: what you did not check, and any risk.
