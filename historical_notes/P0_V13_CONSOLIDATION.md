# P0 v12 -> v13 consolidation

This package keeps the accepted Medium-Solver v05 executable code unchanged and
adds `spec/P0_consolidated_T1_T6_v13.tex` as the active consolidated formal
proposer specification.

The purpose is formal alignment, not a new solver capability.  The executable
v05 DP already contained the behaviors consolidated here through its Python
modules and historical amendments.

## Task-agnostic changes consolidated in v13

1. `PROJECT` is stated explicitly as the fixed representation-level Pair-role
   projection primitive.  Successful primitive F3 use can propose the two
   persistent positional-projection schemas.  This is the generic v03 behavior.
2. F1 mixed stored-procedure reuse accepts exactly one finite component and one
   relation component.  The finite component may be either an explicit
   ALL_ONCE/context residual or a finite role-domain residual inferred from at
   least two complete reference streams, with persistent Pair-role projections
   available.  Ambiguous component modes are rejected.
3. After complete existing-KS search has no survivor, an invocation with
   construction enabled may propose one bounded typed two-component composition
   from already represented parents only: persistent Pair-role projections, a
   same-input-type F3 schema, a same-input-type F4 schema, exactly one
   finite-reference component, exactly one represented relation component, and
   the represented Pair constructor.
4. The transient bounded-construction procedure proposal may carry one
   dependent solution proposal.  Persistence and acceptance remain KSU-owned.
5. F1 candidate generation is restricted to Pair streams, matching the accepted
   v05 executable implementation.

## Explicit non-changes

The consolidation contains no task identifier, expected answer, curriculum-
stage condition, H14-like fixed identifier, or generic abstraction,
generalization, or representation-extension operator.

The construction-control input is task-agnostic.  `T6_pre` remains an external
existing-KS-only experimental control in the accepted v05 replay; normal task
runs use construction enabled and the construction path remains dormant unless
complete local search fails and all represented prerequisites are present.
