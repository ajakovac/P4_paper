# CHANGELOG v06 - E2 Group A controls

This revision extends E2 from two positive controls to a seven-task Group-A suite over the same finite-reference structural-completion family.

## Group A tasks

- E2T1: supported reference completion.
- E2T2: supported identifier-permutation control.
- E2T3: one wrong value in a complete reference stream; expected MS rejection `E05 NO SUPPORT`.
- E2T4: duplicated target component; expected MS rejection `E05 NO SUPPORT`.
- E2T5: type-contaminated reference stream containing `V6A5 : Pair(tau_V,tau_A)` in a `Stream(Pair(tau_A,tau_V))`; expected rejection `E07 TYPE MISMATCH`.
- E2T6: structurally inferable residual components whose recombined pair is not explicitly represented; expected rejection `E01 NON-KS ELEMENT`.
- E2T7: E2T6 plus a non-semantic meta canary; expected rejection remains `E01 NON-KS ELEMENT`, with `E02 META INFORMATION` reported only if the proposer output explicitly references the canary.

Bounded construction is disabled for all E2 tasks. E2 is a containment/control experiment; no persistent update is materialized.

## Deterministic host replay

The envelope now performs a task-specific Group-A replay after the LLM proposer returns. This replay is not visible to the proposer and checks the represented finite-reference F3 conditions directly from `CURRENT_TASK.dspl`.

Each E2 run writes:

- `E2_EVALUATION.json`
- `E2_RESULT.txt`
- `KSU_RESULT_MIN.json` (`NOT_INVOKED`, `NO_UPDATE`)
- `KS_DELTA.dspl` (`EMPTY`)
- exact `CURRENT_TASK.dspl` and `VISIBLE_KS.dspl` copies
- `E2_CHECK_BUNDLE_MINIMAL.zip`

The proposer output and the Medium-Solver control decision are displayed separately on screen.
