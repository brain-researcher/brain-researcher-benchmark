# Structural/support pilot result — 2026-10-04

**Completed the approved source/support and process-isolation pilot. No
connectivity, gradients, scientific endpoints, oracle, or Sol evaluation was run.**

The root launched the frozen package at commit
`5e2354e` with approved contract SHA256
`7eab0a9f8459a99b222ba01dd4f1ff7c981c5818e29468ee63f7f3002773995b`.
All three stages exited zero, with no cleanup errors. Observed stage times were
4.34 s for authentication/staging, 5.94 s for discovery support, and 6.40 s for
held-out support. The result records approximately 127.4 MB of new artifacts,
well below the 1 GiB cap. Container configuration receipts confirm 2 CPU,
8 GiB RAM, no network, and a read-only root filesystem.

## Measured feasibility

- All **46 original source/provenance files** authenticated. The source-derived
  age-pair/hash split exactly matched the frozen 10/10 partition; neither the
  split nor cleaning rule was changed.
- All **10 discovery participants have 400 active parcels**. Frozen discovery
  support is therefore all 400 parcels, with all seven networks retained:
  Vis 61, SomMot 77, DorsAttn 46, SalVentAttn 47, Limbic 26, Cont 52, Default 91.
- **9 of 10 evaluation participants are eligible** on that unchanged support.
  `sub-pixar124` is explicitly source-ineligible because parcel **119**,
  `7Networks_LH_Limbic_TempPole_1`, has a constant extracted parcel-mean time
  series: raw sample SD = 0 and cleaned centered L2 norm = 0. Its geometric
  support contains 68 voxels; this is not an empty-atlas-support failure. The
  public activity threshold is approximately `1.29614814e-11`.
- The person and parcel were not deleted or replaced. The other nine evaluation
  participants remained evaluable. This removes the old all-group-undefined
  cascade without learning a parcel exclusion from evaluation data.

## Isolation and invariance evidence

Each discovery/evaluation process denied **40 opposite-partition file reads**:
20 BOLD/confound files tested at both the capsule path and original baked data
path. All **80 probes** failed as intended. The baked `/app` and
`/opt/source_capture` locations were covered, and the processes ran as nonroot
UID 1004 with dropped capabilities. Evaluation's attempt to open the discovery
artifact for writing was denied.

The discovery artifact SHA256 was unchanged across evaluation:
`e02926d4c402d3773dbd57a3a0abfccdf9b0009db7fd14669daad8321f0bccfb`.
This demonstrates immutable discovery-support transfer in this pilot, **not**
gradient sign/basis invariance on real data; no gradients were computed. The
separate 34 source-free tests cover the prototype arithmetic, contract pins,
launch controls, and timeout/cleanup behavior.

## Evidence and limits

Authoritative artifacts are under:

`/home/zijiaochen/projects/brain_researcher_benchmark/tracking/scientific_pilots_2026-10-04/pr200/`

- `result.json`: bounded completion and 9/10 eligibility.
- `authentication.json`: exact source hashes and metadata-derived split.
- `fit/fit.json`: source-derived discovery diagnostics and frozen support.
- `evaluate/evaluate.json`: all evaluation rows, null reason, and access probes.
- `authenticate.launch.json`, `fit.launch.json`, `evaluate.launch.json`: actual
  commands, container configuration, elapsed times, and exit status.
- Stage `*.stdout.log` files preserve complete combined stdout/stderr.

This pilot reuses the inherited original-byte reader and cleaning primitives.
It is not an independent numerical verifier. The atlas/template mismatch remains
the same disclosed identity-world approximation, not anatomically validated
registration. The data remain previously inspected public movie data; eligibility
does not make the partition pristine or support population/resting-state claims.
No endpoint result or empirical benchmark difficulty is established.

## Recommended next step

Keep the fixed 20-person dataset and this one split; this pilot gives no reason
to expand to 155 people or move the ineligible person. Implement the independent
source-backed support checks and minimal immutable `fit`/`evaluate` interface,
including rejection of invented nulls and test-informed masks. Then review a
separate bounded endpoint-qualification contract for the discovery leading axis
and the nine source-eligible held-out operators, with the tenth person preserved
as a justified null. Only after independent endpoint verification, a complete
oracle, and adversarial controls should a new Sol calibration be launched.
