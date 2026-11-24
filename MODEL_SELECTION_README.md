# Proposer model selection

Every scientific run now begins by choosing a proposer configuration.

1. **PAPER PROFILE** (default): `gpt-5.6-terra`, reasoning effort `medium`. Runs are tagged `paper_replication=YES`.
2. **LEGACY PROFILE**: `gpt-5.6-terra`, reasoning effort `none`. This reproduces the earlier development setting and is tagged `paper_replication=NO`.
3. **CUSTOM MODEL**: enter any model identifier accepted by the installed Codex CLI and one of `none`, `minimal`, `low`, `medium`, `high`, `xhigh`. Custom runs are tagged `paper_replication=NO`.

The selected configuration is written to `PROPOSER_CONFIGURATION.json` in every run directory and in the experiment directory. Reader summaries also show the model, reasoning effort, profile, and whether the run is a paper-profile replication.

A model name that is not supported by the installed Codex CLI or current ChatGPT account produces an execution error. It is not converted into a scientific `NO SOLUTION` result.

For scripted/noninteractive use, the same two selection modes are available:

- predefined: `python runner/run_envelope.py --proposer-profile PAPER experiment --id E3`
- custom: `python runner/run_envelope.py --model MODEL_ID --reasoning-effort high experiment --id E3`

The interactive main menu also contains `M` to change proposer configuration before starting another experiment.
