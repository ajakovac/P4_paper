# Package verification -- v07r1

Verification performed on the packaged source before release:

- Python syntax check for `runner/run_envelope.py`, `runner/e2_group_a.py`, and `runner/e3_composition.py`.
- Envelope `check` command passes.
- Frozen scientific SHA-256 values are unchanged and match `FROZEN_SHA256.json`.
- E3 checkpoint-chain verification passes.
- Explicit Codex model is `gpt-5.6-terra`; the previous `gpt-5.6-sol` pin was rejected by the reported ChatGPT-auth Codex runtime.
- Synthetic transport-failure tests confirm that nonzero/invalid proposer execution is reported as `EXECUTION ERROR` and is not semantically evaluated.
- E2/E3 compact check bundles include `stderr.txt` and `stdout.txt`.
- The actual Codex/LLM calls were not executed in the build environment.
