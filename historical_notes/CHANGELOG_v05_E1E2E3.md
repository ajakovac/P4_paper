# v05 E1/E2/E3 experiment-shell revision

Changes from v04r2:

1. Added `EXPERIMENTS.json` with E1, E2, and E3 groups.
2. Preserved all E1 rows, task files, KS snapshots, frozen hashes, TAEP, P0,
   schemas, and transport semantics.
3. Added provisional E2 tasks `E2T1.dspl` and `E2T2.dspl`.
4. Added `E2_KS_clean.dspl`, containing only type declarations and no
   task-specific solution knowledge.
5. Added an interactive experiment/task menu. Running `run_envelope.py` without
   arguments opens the menu.
6. Added CLI experiment execution: `experiment --id E1|E2|E3` and optional
   `--run-id`.
7. Kept `full` as a backward-compatible alias for E1 only.
8. E3 is a reserved menu choice with no tasks yet.

No expected-answer evaluator was added. E2 expected answers are not supplied to
or stored in the scientific request.
