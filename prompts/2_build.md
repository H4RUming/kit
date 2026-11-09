Work on done criterion [C?] in work/TASK.md section 8 only.
If this session was given a track, the criterion must belong to it: touch only that track's files, stage them by path (never `git add -A` or `git add .`), and stop and report if the section 7 interface needs to change.

1. Plan in 3 lines: files to change, test plan (use the criterion's verification method), expected risk.
2. Show the skeleton BEFORE implementing: function or endpoint names, inputs and outputs, data flow, in under 10 lines. No full code yet. Wait for my confirmation.
3. Implement. Write the test first or together with the code, with the criterion id in the test name as `test_[C?]_...`.
4. Verify only this criterion: `python3 .kit/tools/t.py --note "[C?]" -- python3 -m pytest -q -k [C?]_` (or the criterion's webcheck/dbcheck command). Run the full suite only when I ask or every 2 to 3 criteria.
5. When it passes: local commit, set the status in TASK.md section 8 to 완료 (edit only that cell), update only the "현재 상태" section of work/HANDOFF.md in 3 lines max (with a track, only your track's line), then explain in 3 lines (in Korean): what changed, why this approach and what the alternative was, where it could break. STOP. I will write DECISIONS.md myself from this.
6. If the result differs from what TASK.md says, say so explicitly instead of adjusting silently.
