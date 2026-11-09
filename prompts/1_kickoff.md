Follow AGENTS.md. Do NOT write code yet. Planning (this card, the interview and confirming TASK.md) must fit in 25 minutes, so keep every section short.

1. Read the task README fully and any files it names. For unfamiliar data or folders, use peek for a summary only. Then read the matching `.kit/docs/` files listed in AGENTS.md (web, db, auth).
2. Fill work/TASK.md sections 1 to 5 (in Korean):
   - Section 2: extract EVERY requirement from the README, each with its source line (README:L12).
   - Section 3: fill EVERY constraint category. Write "없음" if none. Never leave a category blank. Environment variable names only, never values.
   - Anything without a source goes to section 5 (assumptions), with what changes if it is wrong.
3. Section 7: if the work has parts that can be built at the same time, draft the interface between them (name, input, output, errors, which track provides and uses it). Otherwise write "없음".
4. Draft section 8 as small done criteria (each about 5 to 10 minutes of work), each linked to requirement ids and with a concrete verification method.
   - C0 comes first: the thinnest version that runs end to end with fake or hard-coded data, following the section 7 interface.
   - Give every criterion a track. A and B must not touch the same files; anything shared is 공통 and is done before the split. List each track's files.
5. If the task requires specific documents or file names, list them.
6. Do NOT write questions. Instead, point out up to 5 places in the README or data that are unclear or contradict each other. For each: location (file:line or column) and one line on how it could change the result.
