"""Assemble a PROVISIONAL movie_facts.json from research/results/*.json.

Field names follow STORYBOARD.md section 6.  Nothing is invented: every value
is copied from the research result files; the file is marked "provisional"
so the final render can be re-run with the verified
research/results/movie_facts.json once the analysis step produces it.

    PYTHONPATH=. python3 facts_provisional.py [--out build/movie_facts.provisional.json]
"""
from __future__ import annotations

import argparse
import json
import os

from common import BUILD_DIR, REPO_DIR

RESULTS = os.path.join(REPO_DIR, "research", "results")


def build() -> dict:
    with open(os.path.join(RESULTS, "onset.json")) as fh:
        onset = json.load(fh)
    with open(os.path.join(RESULTS, "exhaustive.json")) as fh:
        exh = json.load(fh)
    with open(os.path.join(RESULTS, "random.json")) as fh:
        rnd = json.load(fh)
    with open(os.path.join(RESULTS, "random_longest.json")) as fh:
        rnd_longest = json.load(fh)
    adv_path = os.path.join(RESULTS, "adversarial_best.json")
    adv = json.load(open(adv_path)) if os.path.exists(adv_path) else None

    r = onset["results"]
    hw = r["highway"]
    facts = {
        "provisional": True,
        "source_note": "assembled by movie/facts_provisional.py from research/results/*.json; not yet verified",
        "onset_step_empty_grid": int(r["onset_step_s"]),
        "period": int(hw["period"]),
        "displacement_per_period": [int(hw["displacement_per_period"]["dx"]), int(hw["displacement_per_period"]["dy"])],
        "direction_empty_grid": r["certification"]["highway_direction"],
        "ant_at_onset": r["certification"]["ant_at_step_s"],
        "exhaustive": {},
        "random": {
            "total_tested": int(rnd["results"]["totals_main_sweep"]["total_configurations"]),
            "total_highway": int(rnd["results"]["totals_main_sweep"]["total_certified_highway"]),
            "cap_hits": int(rnd["results"]["totals_main_sweep"]["total_cap"]),
            "longest_onset": int(rnd_longest["onset_step"]),
            "longest_config": {
                "k": int(rnd_longest["k"]), "p": float(rnd_longest["p"]), "seed": int(rnd_longest["seed"]),
                "index": int(rnd_longest["sample_index"]), "n_black": int(rnd_longest["n_black"]),
                "black_cells": rnd_longest["black_cells"],
                "regenerate": "research/random/randexp dump {k} {p} {seed} {index}".format(
                    k=rnd_longest["k"], p=rnd_longest["p"], seed=rnd_longest["seed"], index=rnd_longest["sample_index"]),
            },
            "step_cap": int(rnd["parameters"]["step_cap"]),
            "max_k": int(max(rnd["parameters"]["k_values"])),
        },
        "k4_records_csv": exh["results"]["k4"]["per_config_csv"],
        "step_cap_exhaustive": int(exh["parameters"]["step_cap_per_config"]),
    }
    for key, res in exh["results"].items():
        k = str(res["k"])
        if not res.get("exhaustive", False):
            continue  # never merge a partial sweep
        entry = {
            "n_configs": int(res["n_configs"]),
            "n_highway": int(res["n_certified_highway"]),
            "cap_hits": int(res["n_hit_cap"]),
            "max_onset": int(res["onset_step"]["max"]),
            "max_onset_config": {
                "cfg_index": int(res["max_onset_config"]["cfg_index"]),
                "black_cells": res["max_onset_config"]["black_cells"],
                "direction": res["max_onset_config"]["direction"],
            },
        }
        if k == "4":
            entry["histogram_log_bins"] = res["histogram_log_bins"]
        facts["exhaustive"][k] = entry
    if adv is not None:
        runs = adv.get("runs", {})
        facts["adversarial"] = {
            "longest_onset": int(adv["onset_step"]),
            "cap_hits": 0 if not adv.get("any_evaluation_hit_cap", False) else sum(int(v.get("n_non_certified", 0)) for v in runs.values()),
            "n_tested": sum(int(v["n_evals"]) for v in runs.values()),
            "n_highway": sum(int(v["n_evals"]) - int(v.get("n_non_certified", 0)) for v in runs.values()),
            "longest_config": {
                "black_cells": adv["black_cells"],
                "box_k": int(adv["box"]["k"]),
                "direction": adv["direction"],
                "found_in_run": adv.get("found_in_run"),
            },
        }
    return facts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(BUILD_DIR, "movie_facts.provisional.json"))
    args = ap.parse_args()
    facts = build()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(facts, fh, indent=1)
    print(f"wrote {args.out}")
    slim = {k: v for k, v in facts.items() if k not in ("random", "exhaustive", "adversarial")}
    print(json.dumps(slim, indent=1))
    for k, e in facts["exhaustive"].items():
        print(f"exhaustive[{k}]: n_configs={e['n_configs']} n_highway={e['n_highway']} max_onset={e['max_onset']} cap_hits={e['cap_hits']}")
    print("random:", {k: v for k, v in facts["random"].items() if k != "longest_config"})
    if "adversarial" in facts:
        print("adversarial:", {k: v for k, v in facts["adversarial"].items() if k != "longest_config"})


if __name__ == "__main__":
    main()
