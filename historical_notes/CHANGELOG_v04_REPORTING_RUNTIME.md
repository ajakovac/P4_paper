# LLM proposer envelope v04 / P0 v14

This is a reporting/runtime-diagnostic revision only.  The scientific inputs and semantics are unchanged from v03/P0v14.

Unchanged:
- active P0 v14 bytes and SHA-256;
- approved TAEP bytes and SHA-256;
- task DSPL files;
- historical visible-KS snapshots;
- model and isolation configuration;
- transition output schema and protocol;
- construction control manifest;
- no expected answer is supplied to the model.

Changes:
- `SUMMARY.csv` now includes `construction_status`, `overall_outcome`, and `solution`, so T5 is no longer easily misread as an overall failure when its local search correctly returns `no_local_solution` before construction;
- each run writes `RUNTIME_DIAGNOSTIC.json` with measured setup, Codex environment-probe, Codex execution, parsing/validation, post-file, audit, and display timings;
- full curriculum runs also write `RUNTIME_SUMMARY.csv` and `RUNTIME_SUMMARY.txt`;
- the console prints one compact runtime line per episode and a short end-of-curriculum outcome/runtime summary.

All diagnostics are generated after the LLM response or from host-side execution timing.  They are never included in the model request and do not affect proposal evaluation.
