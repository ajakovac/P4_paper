# P0 v13 -> v14 evaluator-semantics amendment

Status: approved conceptual change; task-agnostic; solution-neutral.

P0 v14 leaves the proposal families, curriculum, tasks, visible KS states, bounded-construction semantics, KSU authority, and deterministic executable unchanged. It makes explicit the generic validity conditions already expected of every proposal.

The amendment has two parts. First, the four `candidate_hypothesis` clauses are declared exhaustive for the current restricted profile. This prevents a proposer from treating a type-incompatible or otherwise non-generated rule expression as a candidate while leaving future P0 versions free to add new candidate families explicitly.

Second, the five required checks receive explicit semantics. `proposal_complete` requires the single represented task unknown to be the proposed unknown. `type_compatible` checks the represented unknown and object types. `satisfies_givens` forbids overwriting represented givens and requires the proposal to target the unknown's stream. `satisfies_constraints` evaluates every represented task constraint on the completed candidate state, with unresolved represented conditions never treated as pass. `derivation_supported` requires the binding to be replayable through the P0 derivation semantics.

For `SAME_RELATION_SUCCESSIVE`, the proposal support must commit to a represented relation for the stream, the represented positions must form a complete immediate-successor chain, and that same relation must hold on every represented successive pair after inserting the proposed value. Thus equality of the final value with another valid proposal does not validate an invalid route.

The amendment also states the general validity principle used for later stronger proposers: validity is determined by P0 plus the represented task and visible KS, not by whether the deterministic reference implementation selected the same proposal. A proposal not found or selected by the DP may be valid if it is admitted by the active P0 and passes all required checks.

No task identifier, expected answer, curriculum-stage rule, new procedure family, new KS object kind, new construction operator, or LLM-specific semantic hint is introduced.
