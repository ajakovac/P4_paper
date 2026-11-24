# v07 -- E3 controlled composition

- Preserves the E1 baseline, E2 Group-A tasks, approved TAEP, base P0 v0.14, and transition JSON protocol.
- Adds `P0_E3_EXTENSION_v01.tex`, active only for tasks explicitly tagged `E3_COMPOSITION`.
- Adds E3 starting relations `Rseq` and `Rord`, represented arithmetic primitives, and canonical E3 KS snapshots.
- Adds E3T1, E3T2, E3T3 pre/build/post, and E3T4.
- Adds deterministic host replay for E3 and compact KSU/delta artifacts.
- Stops a complete E3 sequence after a failed formal control, preventing use of later canonical checkpoints after a failed prerequisite update.
- Simplifies E2/E3 console and reader wording to three human-readable outcomes while retaining detailed audit records.
- Adds individual E3 Windows launchers; all launchers retain the final pause.
