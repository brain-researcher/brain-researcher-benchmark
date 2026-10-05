"""Oracle zipapp entrypoint. Reuses the frozen qualified production arithmetic."""
import argparse
import json
from pathlib import Path
import numpy as np
import phase2_production as engine
import source_reader as reader
from phase2_workflow import compute
from format import compact, expand_fit


def load(root, contract, stage):
    manifest = json.loads((root / "source_manifest.json").read_text())
    rows = manifest["files"]
    def raw(role, pid=None):
        found = [r for r in rows if r["role"] == role and r.get("participant_id") == pid]
        if len(found) != 1:
            raise ValueError("source role inventory")
        return reader.read_member(root, found[0])
    labels = reader.parse_lut(raw("atlas_labels"))
    atlas_row = next(r for r in rows if r["role"] == "atlas_image")
    atlas, atlas_affine, _ = engine.decode(raw("atlas_image"), atlas_row["path"].endswith(".gz"), 3)
    ids = contract["discovery_ids" if stage == "fit" else "evaluation_ids"]
    people = []
    for pid in ids:
        bold, affine, _ = engine.decode(raw("bold", pid), True, 4)
        _, records = reader.table(raw("confounds", pid), "\t")
        confounds = np.array([[float(r[n]) for n in contract["confounds"]] for r in records])
        means, counts = engine.extract(bold, affine, atlas, atlas_affine, np.arange(1, 401))
        p = engine.clean(means, confounds, counts)
        p.update(participant_id=pid, raw=means)
        people.append(p)
    return people, labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--fit")
    parser.add_argument("--output", required=True)
    parser.add_argument("--contract", default="/public/contract.json")
    args = parser.parse_args()
    stage = "evaluate" if args.fit else "fit"
    contract = json.loads(Path(args.contract).read_text())
    people, labels = load(Path(args.data), contract, stage)
    frozen = expand_fit(json.loads(Path(args.fit).read_text())) if args.fit else None
    report, _ = compute(stage, people, labels, engine, frozen)
    Path(args.output).write_text(json.dumps(compact(report, stage), allow_nan=False))


if __name__ == "__main__":
    main()
