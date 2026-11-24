# v01r3

Reporting/UX-only revision relative to v01r2.

Changes:

1. Added minimal console progress indicators for every Codex transition run: prepare, Codex running, Codex finished with elapsed time, and POST transport status.
2. After every scientific run, prints a compact RESULT line and compact TRACE line.
3. Writes the same human-readable views as `MINIMAL_RESULT.txt` and `MINIMAL_TRACE.txt` and includes them in the audit bundle with byte-exact hashes.
4. Full-curriculum mode now shows `curriculum i/N` before each independent run.

No change to TAEP, P0, task DSPL, visible-KS DSPL, manifest, transition schema, health semantics, Codex model/configuration, or any expected scientific result.  The new result/trace display is derived only from the already-returned transition JSON; it performs no semantic verification.
