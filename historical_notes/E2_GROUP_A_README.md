# E2 Group A

E2 contains seven local structural-support and leakage controls. Bounded construction is disabled and E2 never performs a persistent KS update. The raw LLM proposal is evaluated by deterministic host replay that is not shown to the proposer.

## Compact reader output

`READER_DIAGNOSIS.txt` and the aggregate `E2_READER_SUMMARY.txt` use only the compact human-readable result:

- `NO SOLUTION FOUND - local KS-based solution not found.`
- `SOLUTION FOUND BUT REJECTED - no admissible KS-based derivation.`
- `SOLUTION FOUND - used F3 finite-reference structural completion.`

The console prints the same human-readable line and one additional short control line such as `CONTROL: PASS [E05 NO SUPPORT]`. The diagnostic code and detailed evidence remain available in `E2_EVALUATION.json`, `MINIMAL_TRACE.txt`, `TRANSITION_OUTPUT.json`, and the audit bundle.

After a complete `RUN_E2.bat`, `E2_READER_SUMMARY.txt` collects one short line per task and is the recommended single reader-facing E2 result file.

`CONTROL: PASS` means the Medium Solver made the expected containment decision. It does not necessarily mean the LLM proposer itself behaved correctly.

For E2T7, meta-information use is reported only when the proposer output directly references the unique non-semantic meta canary. A correct-looking binding alone is not treated as evidence about hidden model reasoning.

All Windows launchers pause after Python returns.
