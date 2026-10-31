# Minimal change (full)
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
