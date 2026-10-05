# Proposed bounded pilot — awaiting root execution approval

`pilot_contract.json` fixes the question, numerical settings, source identities,
selection and resource caps. `pilot.py` defaults to a plan-only command; fitting
requires `--execute`, a separate root approval binding contract/code hashes,
and a resource-capped offline container. **No source fit has been run.**

`launch_pilot.py` is the default-dry-run host entrypoint. It requires an approval
JSON **outside the new evidence directory**, binding the exact contract plus
`pilot.py`, `witness.py` and `launch_pilot.py` hashes. The host deadline starts
before image inspection, so 900 seconds includes source authentication. An
owned-container cleanup grace is separately bounded and recorded, not another
analysis allowance. Read-only mounts, nonroot runtime, CPU/memory/swap limits,
offline networking and disabled GPU visibility are captured before container
start. Logs, create/attach arguments, inspections and failure/cleanup receipts
remain as evidence. A metadata-only probe confirmed the pinned image contains
Python 3.12.3, NumPy 2.1.3 and SciPy 1.14.1; it did not read or fit source data.

## Exact proposed scope

16 deterministic coordinate-bin voxels; b0+1000 and b0+1000+2000; two starts;
free-f fit plus five fixed fraction profiles; two different optimizer routes:
**768 fits maximum**, 1 CPU, 2 GiB, 15 minutes, no GPU/network or automatic retry.
TRF uses an eigenvalue/rotation parameterization. SLSQP uses direct tensor
coefficients with spectral constraints and separately written forward algebra.
They share SciPy/NumPy and data; this is numerical cross-checking, not complete
independent scientific replication.

The proposed domain is λ(D) in [0,.003] mm²/s, S0/measured-b0 in [.5,1.5], and
f in [0,.999]. These are **operational pilot assumptions**, not published
universal tissue/noise bounds. Every fit reports proximity to all domain
boundaries, feasibility separately from solver success, and actual objective
call counts. The model/free-water diffusivity and the two initial spectra are
anchored to Henriques2017 Eq1/Table1; starting orientation/fraction and solver
settings are prospective authoring choices.

The pilot uses found-best **feasible** loss across both routes, not an asserted
global optimum. Finite feasible candidates survive unsuccessful solver
termination as conditional numerical witnesses; optimizer quality is separately
reported. Prespecified loss increments `.005²`, `.01²`, `.02²` are sensitivity
budgets, not likelihood coverage or future pass cutoffs. Candidate pools with
f≤.7, f≤.9 and f≤.999 use the same ceilings. The .7 view is motivated by
Henriques' study-specific high-f caution, not a universal physiological rule.
These views are filtered sparse search pools, **not refitted domain extrema**.

## Provenance and preservation

The runner stream-hashes the three current raw source files against the pinned
manifest. It separately verifies the frozen bank, receipt, public preprocessing
contract and historical independent report hashes. The report must contain a
successful complete-source reconstruction, matching ROI/protocol identity and
zero discrepancy for cached source signals. Only four source-array keys are
loaded from the bank; no old fit parameters, summaries or Sol artifacts enter
the pilot. This authenticates the historical cache lineage; it does not claim
a fresh preprocessing reconstruction.

Output directories must not already exist. Every attempted fit is appended to
`attempts.jsonl`, including failures and mid-fit wall aborts. Every planned
voxel/protocol/budget/view is retained in `report.json`, including no-feasible
and not-attempted states. Partial output is not renamed a successful pilot.

## Review before launch

- Confirm operational bounds and budgets are acceptable for feasibility only.
- Check source/receipt/report hashes, actual image software and resource caps.
- Run source-free tests and independent review, then bind approved exact hashes.
- Launch only the approved container with read-only original-source mounts and
  a new output subdirectory under `tracking/scientific_pilots_2026-10-04/pr156/`.
- Classify resulting evidence as feasibility/conditional sensitivity. No Sol,
  Harbor reward, full-ROI fit or benchmark-release claim is part of this pilot.
