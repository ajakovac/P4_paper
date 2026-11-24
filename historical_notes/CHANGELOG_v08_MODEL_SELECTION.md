# v08 model-selection update

- Added a startup proposer-configuration menu to all Codex-backed run commands.
- Added two predefined profiles: PAPER (`gpt-5.6-terra`, medium) and LEGACY (`gpt-5.6-terra`, none).
- Added CUSTOM MODEL entry for future/reviewer model identifiers plus explicit reasoning effort.
- Added noninteractive CLI equivalents (`--proposer-profile` or `--model` with `--reasoning-effort`).
- Added per-run and per-experiment `PROPOSER_CONFIGURATION.json`; reader summaries now identify the active model configuration.
- Added `paper_replication` tagging so custom/newer-model runs cannot be mistaken for reproduction of the frozen paper profile.
- The selected reasoning effort is enforced through the Codex CLI configuration override `model_reasoning_effort`.
- No E1, E2, or E3 task, visible KS, P0 semantics, expected scientific outcome, or KSU rule was changed.
