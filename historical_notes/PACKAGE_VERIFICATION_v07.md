# Package verification -- v07 E3 composition

Verification performed on the packaged source before release:

- Python syntax check for `runner/run_envelope.py`, `runner/e2_group_a.py`, and `runner/e3_composition.py`.
- Envelope `check` command passes with 24 manifest rows.
- Frozen-file SHA-256 values match `FROZEN_SHA256.json`.
- E3 P0 extension occurs exactly once and is inserted before the single `P0_END` marker for E3 prompts only.
- E3 checkpoint chain verifies: E3KS0 + H_L = E3KS1; E3KS1 + H_W = E3KS2; E3KS2 + H_C = E3KS3; E3KS3 + H_I = E3KS4.
- Synthetic host-replay tests pass for E3T1, E3T2, E3T3_pre, E3T3_build, E3T3_post, and E3T4.
- The E3T3_pre containment control rejects a supplied D28 proposal when H_C is not visible and construction is disabled.
- All Windows batch launchers change to their own package directory and pause before closing.
- E2/E3 reader summaries use compact human-readable outcomes; detailed diagnostic codes remain in the console control line and structured audit files.

The actual Codex/LLM calls were not executed in the build environment because the Codex executable is not available there. They remain runtime operations for the user environment.
