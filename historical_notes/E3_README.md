# E3: controlled composition and reuse

E3 is a positive developmental curriculum using an E3-specific formal extension of P0 v0.14. The base P0, E1, and E2 semantics are unchanged.

Starting KS content:
- `Rseq`: explicit letter succession A->B->C->D->E->F.
- `Rord`: explicit letter sequence numbers A->1, ..., F->6.
- represented elementary procedures `ADD_NAT` and `MUL_NAT` over `NAT_RANGE 0 30`.

Episodes:
- `E3T1`: constructs and admits `H_L`, the later-letter-then-successor procedure.
- `E3T2`: constructs and admits `H_W(L,n)=ord(L)*n`.
- `E3T3_pre`: same E3T3 formal task, existing-KS-only; `H_C` is absent and construction is disabled.
- `E3T3_build`: same formal task and same E3KS2; construction is enabled and may form/admit `H_C`.
- `E3T3_post`: same formal task with E3KS3 containing `H_C`; construction is disabled and the solution must be reuse-based.
- `E3T4`: independent numerical arguments; may form/admit `H_I` from `H_L`, `H_W`, and `ADD_NAT`.

A complete E3 run stops if an episode does not pass its formal host replay, so a later canonical KS checkpoint is never used after a failed prerequisite transition. Individual task launchers intentionally load the canonical prerequisite snapshot for that episode.

## Compact reader output

The screen and `READER_DIAGNOSIS.txt` use three forms:

- `NO SOLUTION FOUND - local KS-based solution not found.`
- `SOLUTION FOUND BUT REJECTED - no admissible KS-based derivation.`
- `SOLUTION FOUND - used ...`

The compact wording is only a reader view. `E3_EVALUATION.json`, `MINIMAL_TRACE.txt`, `TRANSITION_OUTPUT.json`, `KSU_RESULT_MIN.json`, and `KS_DELTA.dspl` retain the detailed evidence.

After a complete run, `E3_READER_SUMMARY.txt` is the recommended single short result file for a reader.
