"""Create fit/val split: val = 20% of train S1 entities, seed 42,
stratified by country x {singleton, non-singleton}. Evaluated vs FULL train pool.
LOCO folds are derived at eval time by country (fit on A, eval on B, full pool).
Writes artifacts/split.json (+ counts to artifacts/metrics/split.json).
Run: .venv/bin/python src/make_split.py
"""

import csv
import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.join(ROOT, "student_resource/dataset/train")

SEED = 42
VAL_FRac = 0.20


def main():
    sing = {}
    with open(os.path.join(TR, "train_ground_truth.tsv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            sing[row["source1_entity_id"]] = (row["matched_entity_ids"] == "")
    strata = {}
    n = 0
    with open(os.path.join(TR, "train_source1.tsv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            eid = row["entity_id"]
            key = (row["country"], sing[eid])
            strata.setdefault(key, []).append(eid)
            n += 1
    assert n == len(sing) == 2206821, (n, len(sing))
    rng = random.Random(SEED)
    val_ids, fit_ids = [], []
    counts = {}
    for key in sorted(strata, key=str):
        ids = strata[key]
        rng.shuffle(ids)
        k = int(round(len(ids) * VAL_FRac))
        val_ids.extend(ids[:k])
        fit_ids.extend(ids[k:])
        counts[str(key)] = {"n": len(ids), "val": k, "fit": len(ids) - k}
    rng.shuffle(val_ids)
    rng.shuffle(fit_ids)
    out = {"seed": SEED, "val_frac": VAL_FRac,
           "stratify": "country x singleton",
           "n_total": n, "n_val": len(val_ids), "n_fit": len(fit_ids),
           "counts": counts, "val_ids": val_ids, "fit_ids": fit_ids,
           "loco": "derive at eval time: fit on country-A S1 entities, eval country-B S1 entities, "
                   "both directions, against FULL train pool"}
    with open(os.path.join(ROOT, "artifacts/split.json"), "w") as f:
        json.dump(out, f)
    with open(os.path.join(ROOT, "artifacts/metrics/split.json"), "w") as f:
        json.dump({"seed": SEED, "val_frac": VAL_FRac, "n_total": n,
                   "n_val": len(val_ids), "n_fit": len(fit_ids), "counts": counts}, f, indent=1)
    print("total=%d val=%d fit=%d" % (n, len(val_ids), len(fit_ids)))
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
