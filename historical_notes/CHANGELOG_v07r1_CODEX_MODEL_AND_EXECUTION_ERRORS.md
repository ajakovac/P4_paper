# v07r1 -- Codex model compatibility and execution-error separation

- Changed the explicit ChatGPT-auth Codex model in `EXPERIMENT_CONFIG.json` from `gpt-5.6-sol` to `gpt-5.6-terra`. The scientific task/KS/P0 content is unchanged.
- A nonzero Codex exit, missing final response, or parse/transport failure is now reported as `EXECUTION ERROR - proposer response not obtained.`
- Technical execution failures are not classified as `NO SOLUTION`, `REJECT`, or a failed scientific Medium-Solver control.
- E2/E3 compact check bundles now include `stderr.txt` and `stdout.txt`.
- E3 stops after an execution error and explicitly states that no scientific task result was recorded.
