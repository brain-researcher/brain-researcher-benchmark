# Reviewed host-side execution snapshot

These are authoring/runtime tools, **not agent-visible task assets**. They are
copied byte-for-byte from the external release evidence directory, after review.
The original execution paths, generated task, frozen approvals/configs and raw
receipts remain at:

`/home/zijiaochen/projects/brain_researcher_benchmark/tracking/scientific_release_2026-10-04/`

This snapshot is retained for code review and provenance, not a portable launcher
to invoke from this subdirectory. Scripts intentionally derive the evidence root
from their location and rely on separately pinned installed Harbor0.17.1 and the
earlier reviewed offline Codex/network adapter. Restore the original reviewed
layout and satisfy the immutable approval gates before execution. No credentials,
source datasets, private numerical answers, generated images or trajectories are
committed here. Do not place these host tools in a coding-agent image.

The Sol launcher permits one GPT-6.1 Sol Max trial only after successful native
oracle, all13 controls, explicit intended-rejection checks and image audits. It
does not turn a model failure into evidence of scientific difficulty.
