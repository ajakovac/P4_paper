P4 ENVELOPE v09r2 — SHORT AND FULL TASK OUTPUT

Launch START_ENVELOPE.py or run_envelope.py from the main folder.
Task statements appear before each Codex call. After each call, the short
output shows the proposer answer/route, KSU decision and reason, admitted
KS elements, and whether persistent KS changed. This is the default.
Menu V toggles SHORT/FULL console output. FULL adds every supplied trace
operation and proposed KS description; a rejected trace is clearly labeled.
The selected mode remains active for this interactive session.

CLI: python run_envelope.py --display full experiment --id E1

Readable files are saved for every new task run:
  runs/V09_.../<run_id>/TASK.txt
  runs/V09_.../<run_id>/MINIMAL_RESULT.txt
  runs/V09_.../<run_id>/FULL_TRACE.txt
Combined task/result output: runs/V09_.../READER_SUMMARY.txt
Raw JSON and audit files are retained as before.

A task is displayed immediately; the result is printed when Codex returns.
This revision does not stream partial model output. Display does not alter
the prompt, task, episode controls, KSU checks, or KS progression.

P4 ENVELOPE v09r1 — INTERACTIVE PYTHON LAUNCHERS

Start from the main extracted folder:
  python run_envelope.py
or:
  python START_ENVELOPE.py

Both open a persistent menu. Choose package checks, local tests, Codex health,
E1/E2/E3, an individual episode, all experiments, model selection or saved errors.
Model selection is requested before the first model call and retained in this
interactive session. Exit code 1 from Codex is not a task-solution rejection:
inspect stderr.txt/stdout.txt; option 9 displays the latest saved failure.

Every BAT launcher now has a corresponding .py launcher in this main folder.
Examples: RUN_E1.py, RUN_E2.py, RUN_E3.py, CHECK_PACKAGE.py, RUN_TESTS.py,
RUN_HEALTH.py, RUN_ONE.py. Run with Python or an editor's Run command.
Paths are resolved relative to the launcher, so the working directory may differ.
Single-action Python launchers pause before closing when used in a terminal.
The BAT files are retained for compatibility; they are not needed.

Existing CLI commands still work from the main folder:
  python run_envelope.py full
  python run_envelope.py --model YOUR_MODEL experiment --id E1

This revision changes launchers and failure reporting only. It does not change
tasks, controls, proposer protocol, KSU admissibility checks or KS progression.
No live LLM calls were made to validate the launchers. The reported exit=1 cannot
be diagnosed without its saved error text; no speculative model change is made.

P4 ENVELOPE v09 — CHECKED SOLUTION PATHS AND KS ADMISSION

Extract the ZIP into a new directory. Python 3.10 or later is required. The
local checks use only the Python standard library. Codex CLI and a configured
account are needed only for live model experiments.

1. Double-click CHECK_PACKAGE.bat (integrity check).
2. Double-click RUN_TESTS.bat (38 local software tests).
3. Double-click START_ENVELOPE.bat, choose the proposer model, then E1/E2/E3.
   Existing RUN_E1.bat, RUN_E2.bat, RUN_E3.bat and individual launchers work.

Command-line examples:
  python runner/run_envelope.py check
  python -m unittest discover -s tests -v
  python runner/run_envelope.py --model YOUR_MODEL --reasoning-effort medium experiment --id E1
  python runner/run_envelope.py --model YOUR_MODEL experiment --id E3

All original task files and manifest construction flags are unchanged.
EPISODE_CONTROLS.json adds explicit proposal/insertion permissions:
- E2: construction, insertion proposals and insertion disabled throughout.
- T6_pre and E3T3_pre: construction, insertion proposals and insertion disabled.
- E3T3_post: construction and insertion disabled; reuse remains possible.
- Developmental episodes retain enabled construction/proposal/insertion.
- T6_post retains the original enabled construction flag. No cleaner comparison
  is silently substituted for this original experimental condition.

An insertion proposal is checked data, never executable Python. A proposed new
procedure may support a dependent construction solution only after KSU has
validated and admitted that procedure. Rejected responses cannot mutate KS.
Ordinary admissible proposals can be evaluated while insertion is disabled;
KSU records them without changing the state. Controls are independent fields.

The proposer may explore using pretrained knowledge. Its public solution path
must use P0 operations and represented CURRENT_TASK/VISIBLE_KS support. The
external verifier replays the route and compares every trace operation; a
correct final answer or self-reported pass flags are insufficient.

Full E1/E3 runs start from the initial snapshot only. Each later invocation
receives the preceding actual KSU state, including represented task observations
and admitted additions from enabled successful episodes. Disabled episodes
leave the KS byte-for-byte unchanged. Observation retention is explicit: current
task DSPL facts are retained at successful insertion-enabled episodes as the
represented support for learning; no inferred solution is added as an input fact.
Prepared later snapshots are used only by isolated episode launchers, labeled
in MODE.json as checkpoint tests, not as a persistent-curriculum demonstration.

Each runs/V09_* directory contains per-episode raw responses, request, visible
KS, KSU_RESULT.json, KS_AFTER.dspl, and audit ZIPs. SUMMARY.json distinguishes
proposer rejection from control containment. NO_LOCAL_SOLUTION is independently
checked against the finite local route family and enabled construction.
Execution errors stop a developmental run; a rejected unsupported answer in a
verified pre-control may be contained without turning it into proposer success.

Serialization changed to KS_CHECKED_V09; CHECKED_PROTOCOL.md is the exact
certificate contract. The old candidate/check-list JSON is not accepted.
P0 supplies solving semantics; the v09 contract supplies the checked output
representation. Reusable additions are restricted to the P0 families exercised
by these tasks. This is not a verifier for arbitrary programs or a proof of
completeness of a general-purpose P0 interpreter. The finite verifier selects
no model response and sends no expected answer/certificate to the proposer.
Its local enumeration verifies failure/construction prerequisites only.

The E3 verifier additionally rejects arithmetic inputs/intermediates/results
outside NAT_RANGE and successor requests beyond represented Rseq. This enforces
the represented domain; the supplied tasks and tested answers are unchanged.

Validation delivered with this package is local software validation with
synthetic proposer responses. No fresh LLM experiments were run. Results from
v08 must not be relabeled as results of this revised verifier or prompt. Live
E1/E2/E3 runs are required for new scientific results.

Original explanatory notes are in historical_notes/. Original snapshots and
P0 files are retained. legacy_transport.py supplies the existing Codex invocation,
model selection and health probe; v09 never uses its old admission runner.
Do not run historical evaluators as the authoritative KSU for v09.
