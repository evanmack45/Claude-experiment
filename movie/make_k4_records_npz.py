"""Pack research/exhaustive/out/k4_records.csv into research/results/exhaustive_k4_records.npz.

    PYTHONPATH=. python3 make_k4_records_npz.py [--csv PATH] [--out PATH]

The CSV (7 MB, gitignored derived data) is produced by research/exhaustive/exhaust; the npz is
the small committed form that the dot wall (S11) and the mosaic assertions (S10) read, so a fresh
clone renders without regenerating the CSV.  Encoding (arrays indexed by config index 0..65535,
the bit encoding of exhaustive.json):

  onset      uint32  the onset step `s` of that configuration
  status     uint8   the CSV `status` column (0 = certified highway)
  direction  int8    highway direction code: bit 0 = +x, bit 1 = +y
                     (0 "-x,-y", 1 "+x,-y", 2 "-x,+y", 3 "+x,+y"); -1 when not certified
  source     str     the CSV path the arrays were packed from
"""
from __future__ import annotations

import argparse
import csv
import os

import numpy as np

import common

DIR_CODE = {"-x,-y": 0, "+x,-y": 1, "-x,+y": 2, "+x,+y": 3}


def pack(csv_path: str, out_path: str) -> dict:
    cfg, onset, status, direction = [], [], [], []
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            cfg.append(int(row["cfg"]))
            onset.append(int(row["s"]))
            status.append(int(row["status"]))
            d = row["dir"].strip().strip('"')
            direction.append(DIR_CODE[d] if int(row["status"]) == 0 and d in DIR_CODE else -1)
    cfg = np.array(cfg, dtype=np.int64)
    n = len(cfg)
    if not np.array_equal(np.sort(cfg), np.arange(n)):
        raise SystemExit(f"{csv_path}: config indices are not exactly 0..{n - 1}")
    order = np.argsort(cfg)
    rec = {
        "onset": np.array(onset, dtype=np.uint32)[order],
        "status": np.array(status, dtype=np.uint8)[order],
        "direction": np.array(direction, dtype=np.int8)[order],
    }
    if int(rec["onset"].max()) > np.iinfo(np.uint32).max:
        raise SystemExit("onset does not fit uint32")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    np.savez_compressed(out_path, source=np.array(os.path.relpath(csv_path, common.REPO_DIR)), **rec)
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=os.path.join(common.REPO_DIR, "research/exhaustive/out/k4_records.csv"))
    ap.add_argument("--out", default=os.path.join(common.REPO_DIR, common.K4_RECORDS_NPZ))
    args = ap.parse_args(argv)
    rec = pack(args.csv, args.out)
    n = len(rec["onset"])
    print(f"wrote {args.out}: {n} configs, {int((rec['status'] == 0).sum())} certified, "
          f"max onset {int(rec['onset'].max())}, {os.path.getsize(args.out)} bytes")


if __name__ == "__main__":
    main()
