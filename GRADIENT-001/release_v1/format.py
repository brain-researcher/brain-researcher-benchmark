"""Small release schema adapters; no source analysis or answer constants."""
import copy
import math


def interpretation(value):
    if value["status"] != "defined":
        return "undefined"
    if value["lower"] > 0:
        return "same_side"
    if value["upper"] < 0:
        return "between"
    return "unresolved"


def person(row):
    out = {key: copy.deepcopy(row[key]) for key in (
        "nuisance_rank", "inactive_on_frozen_support", "source_status", "spectrum", "network_C")}
    out["configuration"] = interpretation(out["network_C"])
    if "transfer" in row:
        out["transfer"] = copy.deepcopy(row["transfer"])
    return out


def compact(report, stage):
    out = {"people": {row["participant_id"]: person(row) for row in report["people"]}}
    if stage == "fit":
        out.update(support=report["parcel_ids"], axis_status=report["axis_status"],
                   axis=report["discovery_axis"], spectrum=report["discovery_spectrum"],
                   network_C=report["discovery_network_C"],
                   configuration=interpretation(report["discovery_network_C"]),
                   leave_one_out={r["omitted_participant"]: {k: v for k, v in r.items()
                       if k != "omitted_participant"} for r in report["leave_one_out"]})
    else:
        out["summary"] = {key: report[key] for key in (
            "n_expected", "n_defined", "mean_fraction", "minimum_fraction", "maximum_fraction",
            "leave_one_valid_person_mean_range")}
    return out


def expand_fit(value):
    axis = value["axis"]
    if axis is not None:
        # The public certificate allows serialized norm roundoff; the frozen
        # prototype's helper is stricter, so normalize only its local input.
        norm = math.sqrt(math.fsum(x*x for x in axis))
        axis = [x/norm for x in axis]
    return {"frozen_support": [i in value["support"] for i in range(1, 401)],
            "discovery_axis": axis, "axis_status": value["axis_status"],
            "discovery_spectrum": value["spectrum"]}
