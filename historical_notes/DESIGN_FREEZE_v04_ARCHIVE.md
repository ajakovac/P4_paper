# LLM proposer envelope v04 / consolidated P0 v14 -- design freeze

## Controlled comparison

The intended comparison keeps task DSPL and visible-KS snapshots fixed and
changes only the proposer implementation:

`same formal P0 + same CURRENT_TASK + same VISIBLE_KS -> DP versus LLM proposer`.

The LLM receives the reviewed task-agnostic, solution-neutral TAEP.  TAEP bytes
are unchanged from the preceding accepted envelope.

## Active formal authority

The active formal proposer specification is:

`frozen/P0_consolidated_T1_T6_v14.tex`

P0 v14 preserves the task-agnostic runtime mechanisms of P0 v13 and makes
the proposal-validity/evaluator semantics explicit. It contains no
expected answer, fixed learned-object identifier, or task-number-dependent
construction trigger.

The frozen P0 v13 and P0 v12 predecessors are retained for audit comparison
but are not sent to the LLM.

## P0 v14 consolidated behaviors

- fixed representation-level `PROJECT` over Pair roles, including task-agnostic
  persistence proposals after successful primitive F3 use;
- F1 mixed stored-procedure reuse with exactly one finite and one relation
  component; finite completion may be explicit-context or reference-inferred;
- Pair-stream-only F1 hypothesis generation, matching the DP-v05 executable;
- after complete existing-KS local failure, optional bounded typed two-component
  composition from represented parents only;
- transient constructed-procedure proposal with conditional dependent solution;
- KSU retains authoritative admission, identifier assignment, and KS mutation.

## Construction control

Construction availability is an invocation-level execution control, not a
curriculum semantic rule.  In this regression manifest all ordinary runs use
`enabled`; the one `T6_pre` invocation uses `disabled` solely as the accepted
existing-KS-only experimental control.  If local search succeeds, the
construction path is not entered even when enabled.

## Envelope responsibility

The envelope is semantically passive.  It verifies frozen input hashes,
assembles role-labelled stdin blocks, starts one fresh isolated Codex process,
uses the strict JSON schema, and records PRE/POST/audit evidence.  It contains
no expected-answer evaluator and makes no KSU/admission decision.

## Transition protocol v02

`LML_PROPOSER_TRANSITION_V02` retains the v01 local candidate, selection, trace,
and knowledge-proposal fields and adds one generic `construction_phase` object.
The schema records serialization only.  Procedure-specific support is returned
as explicit support facts grounded in P0/current task/visible KS.

## Historical-snapshot regression scope

The current envelope still uses the accepted historical KS snapshots for each
curriculum episode.  It therefore tests the proposer transition against the
reference state trajectory but does not yet perform live KSU commits between
LLM calls.  In particular, T5 may propose construction/dependent solution while
T6_post is tested against the frozen historical KS9.

## Health and audit

The transport health test and exact-byte audit behavior are unchanged from
v01r3.  Post-run `MINIMAL_RESULT.txt` and `MINIMAL_TRACE.txt` are display-only
projections of the returned transition and are never supplied to the model.

## P0 v14 evaluator freeze

The v14 change is restricted to generic validity semantics: exact candidate-hypothesis closure for the active profile and explicit semantics for proposal completeness, type compatibility, givens, complete represented constraint checking, and derivation replay. No task or expected answer is added. TAEP bytes remain frozen and unchanged.

## v04 reporting/runtime diagnostic revision

The v04 changes are semantically passive.  The transition request bytes are assembled from the same TAEP, P0, invocation, task, and visible-KS sources as v03.  The transition schema is unchanged.  Post-response reporting now records construction/overall outcome separately and measures host-side runtime phases.  These fields and timings are not sent to the proposer and cannot affect its result.


## v04r2 task/law console reporting

The v04r2 change is display-only.  Before each call, the host prints a compact
view parsed from the already-frozen CURRENT_TASK file.  After the returned
transition is parsed, the host prints the law(s) used by the accepted route and
the rule/procedure support.  These displays are not inserted into REQUEST.txt,
do not modify the transition schema, and cannot affect proposer behavior.
