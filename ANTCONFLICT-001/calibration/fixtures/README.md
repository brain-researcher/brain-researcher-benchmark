# Verifier calibration fixtures

`python tools/check_verifier.py <TASK>` runs `tests/test_outputs.py` once per fixture
directory, with `OUTPUT_DIR` set to `_base/` overlaid with that fixture's files, and
checks each test's outcome against the fixture's `expect.toml`.

- `_base/`: the real numeric outputs from an oracle run (`harbor run ... --artifact
  /app/output`, or `solution/solve.sh` run locally). Copy the small files only
  (CSV/JSON/small .npy). Leave it empty until the oracle has run; until then, assert
  only the prose-graded test(s).
- `<name>/`: the files that differ from `_base`, usually just `findings.md`, plus
  `expect.toml`:

  ```toml
  note = "where this text came from (reference / adversarial / real run <job id>)"
  [expect]
  test_reproduction_recognises_x = "fail"  # list only the tests you are asserting
  "*" = "pass"                              # optional: every other test
  ```

Build the FAIL set from real agent runs. The sentence in which a real agent described its
pipeline is your hardest negative (the SOCIALBRAIN-001 / DEVCONN-001 false passes).
Every fixture's `note` must say where its text came from.

## ANTCONFLICT-001

`_base/` holds the numeric outputs of `solution/compute.py` v2 (one regressor scale per model),
run locally on the Step-0 data cache (2026-10-08). This is not yet an in-container Harbor
oracle run. `reference/` is that run's findings.md verbatim. No agent has run this task yet, so
every other fixture is synthetic, written from the hypothesised failure modes in
`step0/evidence.json` and from a 2026-10-08 review. Replace or extend them with real agent
findings.md files after Stage 5.

- Prose fixtures change only `findings.md`; `unsupported-attribution` also drops the RT analysis
  from `group_results.json`. `negated-rt-explains` and `survives-rt-control` hold the two
  sentences the review showed the v1 verifier passing. The paraphrase fixtures show the fix is
  not a two-sentence blacklist.
- `num-*` fixtures change the numeric outputs and keep the reference prose. They are regenerated
  by `calibration/make_numeric_fixtures.py`. `remove = [...]` in expect.toml deletes a `_base`
  file (`num-user-tamper`, `num-missing-metadata`). `num-alt-pipeline` and
  `num-naive-frame-times` use subject-level values from `step0/alt_pipeline_check.py` and must pass.
