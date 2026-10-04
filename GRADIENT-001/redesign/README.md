# GRADIENT-001: held-out gradient validation (design v1)

Status: **design and source-free prototype only**. This directory does not
replace the evaluated task. No new source extraction, oracle, verifier regrade,
or Sol calibration has been run. Empirical difficulty is unknown.

The question changes from reproducing a large gradient-processing receipt to:
does a leading connectivity axis learned from discovery participants transfer
to other participants, and does the data support the paper-motivated network
configuration? A scientifically correct negative or unresolved result can pass;
an unsupported positive result or blanket `inconclusive` cannot.

Read `draft_instruction.md` for the proposed question, `scientific_contract.json`
for the choices requiring qualification, and `FEASIBILITY_AND_VERIFIER.md` for
the source evidence, qualification gates, and bounded next execution.
`protocol.py` and `test_protocol.py` demonstrate split independence, train-only
support, a sign-invariant transfer statistic, participant-level accounting,
and a basis-invariant network-configuration range. They do **not** authenticate
MRI data or implement a complete benchmark verifier.

Run the source-free controls from this directory:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m pytest -q test_protocol.py
```

The inherited task remains at base commit
`670f98f070c95005c1ebfcc48719a1a68be8717a`; its original outputs and reward remain
untouched. A final numerical bank must not be copied from those agent outputs.
