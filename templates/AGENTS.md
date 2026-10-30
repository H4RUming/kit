# Agent Rules

Priority: task README and exam rules > user instructions > this file. If they conflict, follow the higher one and say so in one line.

## Language
- Reply to the user in Korean. Write TASK.md, DECISIONS.md, HANDOFF.md in Korean. Code, identifiers and commit messages may be English.

## Hard rules (never break)
1. NEVER use Computer Use (screen automation) at any stage: no mouse/keyboard control, no screenshot-driven actions, no automating the built-in Browser. The user checks the Browser manually.
2. Ask the user BEFORE using any browser automation tool (e.g. Playwright).
3. NEVER git push, send files outside, print keys/tokens, modify or kill exam platform settings or proctoring/connection processes, or add dependencies nobody asked for.
4. NO code before the user confirms TASK.md.
5. NEVER claim something works unless a test run passed. Mark checks you could not run as "미검증".
6. Same failure, same kind of fix: max 2 attempts. When t.py prints `[경고]` (repeated failure), STOP. Report 2 cause hypotheses and how to check each, then wait.

## Workflow
1. Understand: read the task README and only the code it touches. For any unfamiliar file, data or folder, run `python3 .kit/tools/peek.py <path>` first, then open only the needed range.
2. Agree: fill TASK.md (goal, facts with source, assumptions, open questions, out of scope, done criteria). Hand open questions to the user.
3. Build: one done criterion at a time, following "Minimal change" below.
4. Verify: after every change run `python3 .kit/tools/t.py` (custom command: `python3 .kit/tools/t.py -- <cmd>`).
5. Record: one line in DECISIONS.md per meaningful decision (decision | reason | rejected option). Local commit after each passed criterion. If the folder is not a git repo, ask before `git init`.
6. Hand off: update HANDOFF.md at the end of each major step or when asked. A new session reads only HANDOFF.md, TASK.md, DECISIONS.md.

## Token discipline
- Before fixing a failure, state its cause in one line. If unknown, investigate first (the log line, the input, a tiny repro). Do not guess-edit.
- `[SAME]` from t.py means nothing changed: do not rerun until you edit a file.
- Run long-output commands (install, build, scripts) via `python3 .kit/tools/q.py -- <cmd>`. Then use `rg`/`sed -n` on the printed log path for details.
- Install quietly (`pip install -q`), and only after `python3 .kit/tools/peek.py --env` shows it is missing. Prefer the standard library.
- Never dump a large file. Use peek, `rg -n`, `sed -n 'A,Bp'`. Do not reread unchanged files.
- Do not start long-running processes (servers). Give the command; the user runs it in another terminal as `<cmd> 2>&1 | tee server.log`. Read it with `tail -n 30 server.log`.
- Keep replies short: files changed, test result, remaining risk. Do not paste code already written to files or long outputs.

## Exam environment
- If the task specifies required documents or file names, write there and move TASK/DECISIONS/HANDOFF content into them. No duplicate content.
- Bind web servers to `0.0.0.0` and print the real port. localhost-only will not open in the Browser preview.
- Avoid heavy processes (loading huge data at once, several servers). Out-of-memory kills are not compensated.

## End of every reply
One or two lines: what you did not check, and any risk the user must know.

## Minimal change
Adapted from Ponytail AGENTS.md (DietrichGebert/ponytail, MIT License, Copyright (c) 2026 DietrichGebert).

Before writing: read the task and the code it touches. List every place the change must reach (callers, tests, fixtures, config, exports) and what it could break for users (data loss or exposure, broken callers). That is scope. Extra features are not.

Take the first option that fully works:
1. Does it need to exist? Skip features, options and flexibility nobody asked for, and name them in one line.
2. Already in this codebase? Use it the way surrounding code does.
3. Standard library or platform feature? Use it.
4. Installed dependency? Use it. Never add a dependency for a few lines.
5. One readable line? One line.
6. Otherwise, the minimum code that works.

- Lazy about the solution, never about the change: fix the callers, tests and fixtures your change breaks.
- No abstraction, wrapper, option, config or "for later" code nobody asked for. Keep existing structure and conventions. Deletion beats addition.
- Comment only the why, in one line.
- Bug fix: grep every caller first, then fix the root cause once in shared code.
- Between equal-size options, pick the one correct on edge cases.
- New non-trivial logic (branch, loop, parser, money, security) gets one small test or assert.
- Known-limit shortcut gets a comment: `shortcut: <limit>, <when to upgrade>`.

Never cut: validation at trust boundaries, error handling that prevents data loss, security, accessibility, anything the user asked for.
