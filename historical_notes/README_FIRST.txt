P4 LLM PROPOSER ENVELOPE v07 / E1-E2-E3
===========================================

QUICK START
-----------
Double-click `START_ENVELOPE.bat`, or run:

  python runner\run_envelope.py

The interactive menu offers:

  E1  Baseline developmental curriculum
  E2  Group A: local structural-support and leakage controls
  E3  Controlled composition and reuse

Run a complete experiment or select an individual episode. E3 also has
`RUN_E3Tn_ONLY.bat` launchers, including separate pre/build/post launchers for E3T3.
All Windows launchers pause after Python returns.

SCIENTIFIC SCOPE
----------------
E1 and E2 retain the approved TAEP and base P0 v0.14 semantics. E3 adds a
separate formal extension, `frozen/P0_E3_EXTENSION_v01.tex`, which is inserted
into the normative P0 block only for tasks explicitly tagged E3_COMPOSITION.

E3 starts from explicit represented letter succession (`Rseq`), explicit letter
sequence numbers (`Rord`), and represented finite arithmetic primitives. It
therefore does not license ordinary pretrained alphabetic knowledge as formal
support. See `E3_README.md` and `E3_EXPECTED.json`.

READER OUTPUT
-------------
For E2 and E3, the screen and per-run `READER_DIAGNOSIS.txt` use compact wording:

  NO SOLUTION FOUND - local KS-based solution not found.
  SOLUTION FOUND BUT REJECTED - no admissible KS-based derivation.
  SOLUTION FOUND - used ...

After a complete run use `E2_READER_SUMMARY.txt` or `E3_READER_SUMMARY.txt`.
Detailed evidence remains in the evaluation JSON, transition output, minimal trace,
KSU result, KS delta, and audit bundle.

E3 DEVELOPMENTAL CONTROL
------------------------
E3T3_pre and E3T3_post use the same formal E3T3 task. The pre episode sees E3KS2
without H_C and has construction disabled; E3T3_build may construct/admit H_C;
the post episode sees E3KS3 containing H_C and again has construction disabled.
A complete E3 run stops after any failed formal control rather than continuing
with a later canonical checkpoint.

`RUN_FULL_CURRICULUM.bat` remains a backward-compatible E1-only run.
`START_ENVELOPE.bat` option A runs all populated experiment groups.

--------------------------------------------------------------------
ARCHIVED v04r2 README CONTENT FOLLOWS
--------------------------------------------------------------------

LLM PROPOSER ENVELOPE v04r2 / P0 v14
==================================

Purpose
-------
This package keeps the reviewed task-agnostic execution prompt (TAEP) unchanged
and changes the active formal semantic authority from consolidated P0 v13 to
P0 v14. P0 v14 preserves the v13 runtime mechanisms and makes the generic
proposal-validity and evaluator semantics explicit.

TAEP STATUS
-----------
APPROVED: TASK_AGNOSTIC_EXECUTION_PROMPT_V01
SHA256: d7525a94fcfcb6f4fbf983ff3f901e60dc1ce6ab0c9af25ca53683d1214ca0ce

The TAEP contains no task identifier, expected answer, preferred procedure, or
English restatement of F0/F1/F3/F4 semantics.  Its bytes are unchanged from the
previous frozen LLM experiment.

ACTIVE FORMAL P0
----------------
- frozen/P0_consolidated_T1_T6_v14.tex

Frozen predecessors are retained for comparison:
- frozen/P0_consolidated_T1_T6_v13.tex
- frozen/P0_consolidated_T1_T5_v12.tex

P0 v14 retains the v13 task-agnostic mechanisms:
- generic Pair-role PROJECT execution and positional-projection persistence;
- F1 mixed reuse with exactly one finite component and one relation component,
  where finite completion can be explicit-context or reference-inferred;
- bounded typed component composition after complete existing-KS failure;
- transient construction procedure proposal plus conditional dependent solution;
- Pair-stream-only F1 hypothesis generation, matching the accepted DP-v05 code.

The P0 contains no task-specific expected value, H14-like fixed identifier, or
curriculum-stage construction rule.

TRANSITION PROTOCOL V02
-----------------------
The JSON output adds a generic construction_phase object.  It records whether
construction was allowed, whether a construction proposal was produced, and an
optional dependent solution.  Procedure-specific construction support remains
explicit support facts; the output schema is serialization only.

RUN ORDER
---------
Recommended first checks after this formal change:

  CHECK_PACKAGE.bat
  RUN_T5_ONLY.bat
  RUN_T6_POST_ONLY.bat

Then, if those are satisfactory:

  RUN_FULL_CURRICULUM.bat

T6_pre remains the accepted existing-KS-only experimental control: its formal
T6 task and KS8 are unchanged, construction is disabled only for that control
invocation, and no persistent update is performed by this regression envelope.
All normal episodes have construction enabled; the path remains dormant unless
complete local search fails and P0 prerequisites are represented.

INPUT ISOLATION
---------------
Each Codex call receives only these role-labelled stdin blocks:
  TAEP
  P0
  INVOCATION
  CURRENT_TASK
  VISIBLE_KS

No expected answer, deterministic output, future task, or regression oracle is
inserted into the request.

SCOPE
-----
This bundle is still a regression envelope over the accepted historical KS
snapshots.  It does not yet perform live KSU commits between LLM calls.  Thus a
T5 construction proposal can be tested, while T6_post is run against the frozen
historical KS9 containing the independently accepted procedure from the DP
reference trajectory.

P0 v14 note: the TAEP, tasks, KS snapshots, model/configuration, and output protocol are unchanged. The only scientific change from v02/P0v13 is explicit task-agnostic proposal-validity/evaluator semantics and closed candidate-hypothesis generation under the current profile.

REPORTING / RUNTIME DIAGNOSTICS IN v04
--------------------------------------
This revision does not change the scientific experiment.  `SUMMARY.csv` now distinguishes local outcome, construction status, overall outcome, and solution.  For example, T5 can correctly show `local_outcome=no_local_solution` together with `construction_status=construction_proposed` and `overall_outcome=solution_proposed`.

Each episode also writes `RUNTIME_DIAGNOSTIC.json`.  A full curriculum additionally writes `RUNTIME_SUMMARY.csv` and `RUNTIME_SUMMARY.txt`, and prints compact timing information in the console.  These host-side diagnostics are never shown to the LLM.


CONSOLE REPORTING IN v04r2
---------------------------
Before each scientific transition call, the batch window prints a compact view
of the frozen current task (input stream(s), unknown, explicit task laws /
constraints, and available relations where declared).  After the response, the
result block prints the solution prominently, then the law(s) used by the
accepted route, followed by the rule/procedure support.  This is host-side
reporting only and is never supplied to the LLM.


V07R1 CODEX MODEL NOTE
The package explicitly requests gpt-5.6-terra for ChatGPT-auth Codex runs.
Change EXPERIMENT_CONFIG.json only if another model is known to be enabled for the account/workspace.
A Codex execution failure is reported as EXECUTION ERROR and is not interpreted as a scientific no-solution result.
