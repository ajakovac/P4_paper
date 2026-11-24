# Change log: LLM proposer envelope v03 / P0 v14

Scientific change from v02/P0v13: replace active P0 v13 by P0 v14. The TAEP, tasks, visible KS snapshots, model/configuration, transition schema, transport, and curriculum manifest are unchanged.

P0 v14 explicitly defines the five required evaluator checks over the complete proposal tuple and represented task state, including full `SAME_RELATION_SUCCESSIVE`, component ALL_ONCE, and component-relation checking. It also states that the four current `candidate_hypothesis` clauses are exhaustive for the restricted profile.

This prevents a numerically correct value from validating an inadmissible or constraint-violating route, while preserving the more general principle that a proposal need not match the deterministic reference implementation if it is admitted by P0 and passes every required check.

No task-specific entity, expected answer, solution hint, curriculum-stage condition, new procedure family, new construction operator, or TAEP semantic rule is added.
