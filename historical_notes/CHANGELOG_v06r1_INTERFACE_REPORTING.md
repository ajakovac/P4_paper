# CHANGELOG v06r1 - Windows launcher and reader-facing E2 diagnosis

This revision does not change the frozen P0, E1 curriculum, E2 task definitions, visible KS files, or E2 decision semantics.

## Windows launcher correction

The E2T3--E2T7 single-task launchers in v06 lacked a final `pause`, so a console opened by double-click could close as soon as the Python process returned. All batch launchers are now normalized to:

- change to the package directory with `cd /d "%~dp0"`;
- preserve the Python exit code;
- print the exit code;
- keep the console open until a key is pressed.

## Reader-facing diagnosis

Every E2 run now writes `READER_DIAGNOSIS.txt`, containing a concise human-readable interpretation of the raw proposer result and the Medium-Solver decision. It is included in `E2_CHECK_BUNDLE_MINIMAL.zip`.

A complete E2 experiment also writes `E2_READER_SUMMARY.txt`, which concatenates the reader diagnoses for all seven Group-A tasks. This is the recommended single file for a reader who wants the experimental result without inspecting JSON or the full trace.

The existing `E2_RESULT.txt` remains as a terse status record, and `E2_EVALUATION.json` remains the authoritative structured diagnostic record.
