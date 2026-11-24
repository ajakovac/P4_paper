# P4 Envelope v09r2

P4 Envelope provides launchers and checked solution paths for the E1, E2, and E3 experiments. The current revision displays task statements and results in short or full form and saves readable output for each new task run.

## Requirements

- Python 3.10 or later. Local checks use only the Python standard library.
- Codex CLI and a configured account are required for live model experiments, but not for local checks.

## Getting started

Extract the package into a new directory and run the following from the main folder:

```bash
python CHECK_PACKAGE.py
python RUN_TESTS.py
python START_ENVELOPE.py
```

Alternatively, start the interactive menu with `python run_envelope.py`. The menu provides package checks, local tests, a Codex health check, E1/E2/E3, individual episodes, all experiments, model selection, and saved errors. Model selection is requested before the first model call and retained for the interactive session.

On Windows, the corresponding `.bat` launchers remain available. Each has a Python counterpart, including `RUN_E1.py`, `RUN_E2.py`, `RUN_E3.py`, `RUN_HEALTH.py`, and `RUN_ONE.py`. Launcher paths are resolved relative to the launcher, so the working directory may differ. Single-action Python launchers pause before closing when used in a terminal.

### Command-line examples

```bash
python runner/run_envelope.py check
python -m unittest discover -s tests -v
python run_envelope.py full
python run_envelope.py --model YOUR_MODEL experiment --id E1
python runner/run_envelope.py --model YOUR_MODEL --reasoning-effort medium experiment --id E1
python runner/run_envelope.py --model YOUR_MODEL experiment --id E3
python run_envelope.py --display full experiment --id E1
```

A Codex exit code of 1 is not a task-solution rejection. Inspect `stderr.txt` and `stdout.txt`; menu option 9 displays the latest saved failure.

## Output

Task statements appear before each Codex call; results appear when Codex returns. Partial model output is not streamed. Short output is the default and shows the proposer answer and route, KSU decision and reason, admitted KS elements, and whether persistent KS changed. Menu option **V** toggles short and full output for the current interactive session. Full output also includes every supplied trace operation and proposed KS description, with rejected traces clearly labeled. Display mode does not change prompts, tasks, episode controls, KSU checks, or KS progression.

Each new task run saves readable files:

```text
runs/V09_.../<run_id>/TASK.txt
runs/V09_.../<run_id>/MINIMAL_RESULT.txt
runs/V09_.../<run_id>/FULL_TRACE.txt
runs/V09_.../READER_SUMMARY.txt
```

`READER_SUMMARY.txt` combines task and result output. Raw JSON and audit files are retained. Run directories also contain per-episode responses, requests, visible KS, `KSU_RESULT.json`, `KS_AFTER.dspl`, and audit ZIPs. `SUMMARY.json` distinguishes proposer rejection from control containment.

## Experiment controls and verification

`EPISODE_CONTROLS.json` specifies independent construction, insertion-proposal, and insertion permissions:

- E2, `T6_pre`, and `E3T3_pre` disable construction, insertion proposals, and insertion.
- `E3T3_post` disables construction and insertion; reuse remains possible.
- Developmental episodes retain enabled construction, proposal, and insertion.
- `T6_post` retains the original enabled construction flag; no cleaner comparison is substituted for that experimental condition.

Insertion proposals are checked data, not executable Python. A proposed procedure can support a dependent construction solution only after KSU validates and admits it. Rejected responses cannot mutate KS. Admissible proposals can be evaluated while insertion is disabled; KSU records them without changing the state.

The proposer may explore using pretrained knowledge, but its public solution path must use P0 operations and represented `CURRENT_TASK`/`VISIBLE_KS` support. The external verifier replays the route and compares every trace operation; a correct answer or self-reported pass flags are not sufficient. `NO_LOCAL_SOLUTION` is independently checked against the finite local route family and enabled construction. The E3 verifier also rejects arithmetic inputs, intermediate values, and results outside `NAT_RANGE`, and successor requests beyond represented `Rseq`.

Full E1/E3 runs start from the initial snapshot. Each subsequent invocation receives the preceding actual KSU state, including represented task observations and admitted additions from enabled successful episodes. Disabled episodes leave KS byte-for-byte unchanged. Current task DSPL facts are retained at successful insertion-enabled episodes as represented support for learning; no inferred solution is added as an input fact. Isolated episode launchers use prepared later snapshots, labeled as checkpoint tests in `MODE.json`, rather than demonstrating a persistent curriculum. Execution errors stop a developmental run; a rejected unsupported answer in a verified pre-control can be contained without becoming a proposer success.

The checked serialization is `KS_CHECKED_V09`; see [CHECKED_PROTOCOL.md](CHECKED_PROTOCOL.md) for the exact certificate contract. The old candidate/check-list JSON is not accepted. P0 supplies solving semantics, while v09 supplies the checked output representation. Reusable additions are limited to the P0 families exercised by these tasks; this is not a verifier for arbitrary programs or a proof of completeness of a general-purpose P0 interpreter. The finite verifier selects no model response and sends no expected answer or certificate to the proposer; its local enumeration verifies failure and construction prerequisites only.

## Validation and historical material

The package's reported validation is local software validation with synthetic proposer responses; no fresh LLM experiments were run for this revision. Results from v08 must not be relabeled as results of the revised verifier or prompt. New scientific results require live E1/E2/E3 runs.

Original explanatory notes are in `historical_notes/`; original snapshots and P0 files are retained. `legacy_transport.py` supplies the existing Codex invocation, model selection, and health probe, but v09 does not use its old admission runner. Do not use historical evaluators as the authoritative KSU for v09.

For the original version notes and instructions, see [README_FIRST.txt](README_FIRST.txt).
