# v01r1 change log

Health/audit corrections only:

- removed dynamic expected-canary enums from the health output schema;
- generate fresh opaque canaries for every health run;
- use a true multiline canary containing a literal LF;
- compare canaries host-side after model output;
- write generated audit text as exact UTF-8/LF bytes on all platforms;
- hash the exact bytes written to request/stdout/stderr/final files;
- include `AUDIT_FILE_SHA256.json` in each audit bundle.

No P0, scientific TAEP, task DSPL, KS DSPL, manifest, transition output schema,
or scientific proposer semantics were changed.
