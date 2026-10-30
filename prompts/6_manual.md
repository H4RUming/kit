Write a manual Browser checklist for done criterion [C?] that webcheck cannot cover (JS-rendered UI, clicks, input flows). Do NOT automate the browser.

- Port and path to open in the Browser tool
- At most 5 steps, each: what I do, then what I should see (in Korean, one line each)
- Include one failure case (empty input, wrong value, refresh)

After I report the results, append one line per step to work/VERIFY.md:
`- <time> | MANUAL | [C?] <step> | PASS or FAIL | <what I saw>`
If any step failed, state the likely cause in one line before proposing a fix.
