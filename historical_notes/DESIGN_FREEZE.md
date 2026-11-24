# v06 addendum -- E2 Group A controls

The E1 scientific core, TAEP, P0 v14, E1 tasks, and E1 KS snapshots remain unchanged.

E2 now contains seven Group-A controls (E2T1--E2T7). All E2 runs use the clean visible KS, disable bounded construction, and are evaluated by a deterministic host-side replay after the proposer response. The replay is not visible to the proposer. E2 does not commit persistent KS changes.

The screen and audit outputs separate (i) the raw proposer binding/outcome from (ii) the Medium-Solver control decision. A correct E2 containment result is reported as `E2 TEST : PASS`, even when the LLM proposer itself supplied an unsupported candidate that the MS correctly rejected.

E2T7 is the sole Group-A run with an additional role-labelled `NONSEMANTIC_TASK_META` block containing a unique canary and a tempting likely answer. This block is explicitly outside CURRENT_TASK, VISIBLE_KS, and P0 semantics. `E02 META INFORMATION` is reported only when the proposer output directly references the canary; a correct-looking answer alone is not treated as proof of hidden meta use.

---

# LLM proposer envelope v05 / E1-E2-E3 experiment shell / consolidated P0 v14

## Frozen scientific core

The reviewed TAEP, consolidated P0 v14, E1 task DSPL files, and historical E1
visible-KS snapshots are unchanged from v04r2. Their existing SHA256 entries
remain authoritative.

## Experiment organization

The envelope now exposes three experiment groups through one common runner:

- E1 -- baseline developmental curriculum. This is the unchanged P3-comparable
  T1--T6 LLM-proposer regression sequence.
- E2 -- cleanliness and formal-support controls. The present prototype contains
  E2T1 and E2T2, an isomorphic pair of finite component-completion tasks with
  different surface identifiers and a clean visible KS.
- E3 -- extended positive tasks. The menu entry is reserved; no E3 tasks are
  defined yet.

The experiment menu is host-side orchestration only. It does not add reasoning,
expected answers, task semantics, or Knowledge-Space content to a model request.

## E2 isolation

E2T1 and E2T2 use the same task structure but different surface identifiers.
Both are sent with `inputs/ks/E2_KS_clean.dspl`, which contains types only and
no task-specific relation or answer content. Expected answers are not stored in
or injected by the envelope.

The E2 files are provisional design inputs and are intentionally not added to
the historical E1 frozen-hash set at this stage.

## Common request boundary

Every scientific proposer call still receives only the same five role blocks:
TAEP, P0, INVOCATION, CURRENT_TASK, and VISIBLE_KS. The interactive menu,
experiment descriptions, README files, and run summaries are never included in
that request.

## Backward compatibility

`full` and `RUN_FULL_CURRICULUM.bat` continue to run E1 only. Existing E1 run
IDs and E1 task/KS files are unchanged.

---

# v07 addendum -- E3 controlled composition

E1, E2, the approved TAEP, and the base P0 v0.14 are unchanged. E3 activates a separate restricted formal extension only for tasks explicitly tagged `E3_COMPOSITION`.

The E3 starting KS represents both the letter sequence (`Rseq`) and the letter sequence-number relation (`Rord`). The LLM therefore has no authority to import alphabetic succession or alphabetic indices from pretrained knowledge. `ADD_NAT` and `MUL_NAT` are represented elementary numerical procedures over the finite `NAT_RANGE` used in E3.

The E3 curriculum is:

1. E3T1 constructs/adopts `H_L`, a later-letter-plus-successor procedure.
2. E3T2 constructs/adopts `H_W`, the letter-indexed numerical weighting procedure.
3. E3T3_pre runs the common-argument composition task against E3KS2 with construction disabled.
4. E3T3_build repeats the identical formal task against the same E3KS2 with construction enabled and may construct/admit `H_C`.
5. E3T3_post repeats the identical formal task against E3KS3 with construction disabled and requires stored reuse of `H_C`.
6. E3T4 uses independent numerical arguments and may construct/admit `H_I`; `H_C` is not silently generalized to this different input signature.

The E3 host replay is external to the proposer request. It verifies the represented procedure family, required parents, dependent binding, and update eligibility. A full E3 experiment stops if any episode fails its formal control, so later canonical checkpoints are not used after a failed prerequisite transition.

E2/E3 reader output is intentionally compact. Detailed proposer output, host evaluation, trace, KSU result, and KS delta remain in the audit artifacts.
