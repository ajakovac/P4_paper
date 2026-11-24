# v04r2 task/law console reporting

Reporting-only revision.

Changes:

- prints a compact `ORIGINAL TASK` block before each LLM call;
- lists the task input stream(s) with the unknown shown as `?`;
- lists explicit task law(s)/constraint(s) and available relations when present;
- prints `LAW(S) USED BY SOLUTION` in the result block;
- retains the existing prominent `SOLUTION`, `RULE / PROCEDURE`, local-search, and construction lines.

No change was made to P0, TAEP, task files, KS snapshots, transition schema,
manifest, model configuration, or semantic execution.  The new text is derived
only from the frozen task file and the already-returned transition output.
