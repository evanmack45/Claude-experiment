#!/usr/bin/env python3
"""Fill the results table in README.md from research/results/exhaustive.json."""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "..", "results", "exhaustive.json")))
rows = ["| k | configs | certified highway | hit cap | boundary | s min | s mean | s median | s max | max-s configuration (black cells) | directions +x,+y / +x,-y / -x,+y / -x,-y | max steps any run | total steps | wall s |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for k, r in d["results"].items():
    o = r["onset_step"]; m = r["max_onset_config"]; dc = r["direction_counts"]
    rows.append("| %d | %d | %d | %d | %d | %d | %.1f | %s | %d | %s | %d / %d / %d / %d | %d | %d | %.0f |" % (
        r["k"], r["n_configs"], r["n_certified_highway"], r["n_hit_cap"], r["n_hit_grid_boundary"],
        o["min"], o["mean"], o["median"], o["max"], json.dumps(m["black_cells"]).replace(" ", ""),
        dc["+x,+y"], dc["+x,-y"], dc["-x,+y"], dc["-x,-y"],
        max(p["max_steps_any_run"] for p in r["compute"]["parts"]), r["compute"]["total_steps"],
        max(p["elapsed_s"] for p in r["compute"]["parts"])))
rows.append("")
rows.append("Log-spaced onset-step histograms (10 bins/decade) are in `results.k*.histogram_log_bins` of the JSON; exact histograms in `out/k*_hist_exact.csv`.")
p = os.path.join(HERE, "README.md"); s = open(p).read()
s = re.sub(r"RESULTS_TABLE_PLACEHOLDER|(\| k \| configs.*?)(?=\n\n## Sanity)", lambda _: "\n".join(rows), s, flags=re.S)
open(p, "w").write(s); print("README table updated")
