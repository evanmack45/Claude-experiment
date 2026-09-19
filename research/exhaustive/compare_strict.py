"""Compare the strict-certificate pass (out/strict) with the default pass (out/) and write
../results/exhaustive_strict.json. Run from anywhere; paths are relative to this file."""
import json, os, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
RES = os.path.join(HERE, "..", "results")
CAP = 5_000_000


def load_summary(path):
    txt = open(path).read()
    # the cell lists are nested ([[x,y],...]); blank them before parsing
    txt = re.sub(r'"argmax_cells": \[(?:\[[^\]]*\],?)*\]', '"argmax_cells": []', txt)
    txt = re.sub(r'"argmin_cells": \[(?:\[[^\]]*\],?)*\]', '"argmin_cells": []', txt)
    return json.loads(txt)


def hist(path):
    return np.fromfile(path, dtype=np.uint32)


def exact_hist_from_csv(path):
    h = np.zeros(CAP + 1, dtype=np.uint32)
    for line in open(path):
        if line.startswith("s") or not line.strip():
            continue
        s, c = line.strip().split(",")[:2]
        h[int(s)] = int(c)
    return h


result = {"experiment": "exhaustive_strict", "conventions": "CONVENTIONS.md",
          "description": "Every configuration in the k x k box (k=1..5) re-run with the strict highway certificate "
                         "of exhaust.c (heading periodicity, 20-cell margin at every position of the last period, "
                         "period footprint narrower than the 20-period displacement). Onset histograms must be "
                         "bit-identical to the default pass; certification steps may be later.",
          "per_k": {}}
ok_all = True
for k in range(1, 6):
    if k < 5:
        strict = load_summary(os.path.join(OUT, "strict", f"k{k}_summary.txt"))
        hs = hist(os.path.join(OUT, "strict", f"k{k}_hist.bin"))
        parts = [strict]
    else:
        parts = [load_summary(os.path.join(OUT, "strict", "k5", f"half{i}_summary.txt")) for i in (0, 1)]
        hs = hist(os.path.join(OUT, "strict", "k5", "half0_hist.bin")) + hist(os.path.join(OUT, "strict", "k5", "half1_hist.bin"))
    n = sum(p["n_configs"] for p in parts)
    ncert = sum(p["n_certified"] for p in parts)
    ncap = sum(p["n_cap"] for p in parts)
    nb = sum(p["n_boundary"] for p in parts)
    nnt = sum(p["n_nontraveling_periodic"] for p in parts)
    smax = max(p["s_max"] for p in parts)
    maxcert = max(p["max_cert_steps"] for p in parts)
    ndisp = sum(p["n_disp_not_2_2"] for p in parts)
    # default-pass histogram: exact csv committed next to the results
    csv_default = os.path.join(OUT, f"k{k}_hist_exact.csv")
    if not os.path.exists(csv_default):  # fresh clone: use the committed copy
        csv_default = os.path.join(RES, "histograms", f"exhaustive_k{k}_onset_hist_exact.csv")
    hd = exact_hist_from_csv(csv_default)
    identical = bool(np.array_equal(hs, hd))
    ok = identical and ncert == n == (1 << (k * k)) and ncap == nb == nnt == 0 and ndisp == 0
    ok_all &= ok
    result["per_k"][f"k{k}"] = {"n_configs": n, "n_certified_strict": ncert, "n_cap": ncap, "n_boundary": nb,
                                "n_nontraveling": nnt, "n_disp_not_pm2_pm2": ndisp, "max_onset": smax,
                                "max_certification_step_strict": maxcert,
                                "onset_histogram_identical_to_default_pass": identical, "all_ok": ok}
    print(f"k={k}: {ncert}/{n} strict-certified, cap={ncap} boundary={nb} nontravel={nnt} disp!=2={ndisp}, "
          f"max onset {smax}, max cert step {maxcert}, histogram identical: {identical}")
result["all_configurations_strictly_certified"] = ok_all
json.dump(result, open(os.path.join(RES, "exhaustive_strict.json"), "w"), indent=1)
print("wrote results/exhaustive_strict.json; all ok:", ok_all)
