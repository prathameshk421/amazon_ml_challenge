"""Confirm a trained run on a held-out feature set (default: MATCH_VALID), paired vs a reference run.

Ensures <parent>_<SET>_pairs.parquet exists (via the parent's own predict_run if needed;
that is exactly what the parent model outputs at test time), scores the run with predict_run,
applies its saved decision, and reports paired per-entity F0.5 vs the reference per-entity file.

Usage: python confirm_valid.py --run M038 --parent M027 --set MATCH_VALID
Writes: work/match/runs/<run>/<SET>_pairs.parquet, <SET>_per_entity.npy, confirm_<SET>.json
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "submission",
        "code",
        "business_entity_resolution",
        "src",
    ),
)
from ber import exp, io_utils, match  # noqa: E402


def ensure_pairs(run, set_name):
    rd = match.runs_dir(run)
    pp = rd / f"{set_name}_pairs.parquet"
    if pp.exists():
        return
    doc = io_utils.read_json(rd / "models" / "matcher.json")
    _, _, s1, pool, _, p_cal, _ = exp.predict_run(set_name, doc, rd / "models")
    pd.DataFrame(
        {"s1_idx": s1, "pool_idx": np.asarray(pool), "p": np.asarray(p_cal, dtype=np.float32)}
    ).to_parquet(pp)
    print(f"wrote {pp} ({len(s1)} rows)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--parent", required=True)
    ap.add_argument("--set", default="MATCH_VALID")
    args = ap.parse_args()

    ensure_pairs(args.parent, args.set)
    rd = match.runs_dir(args.run)
    doc = io_utils.read_json(rd / "models" / "matcher.json")
    _, _, s1, pool, _, p_cal, p_raw = exp.predict_run(args.set, doc, rd / "models")
    pd.DataFrame(
        {"s1_idx": s1, "pool_idx": np.asarray(pool), "p": np.asarray(p_cal, dtype=np.float32)}
    ).to_parquet(rd / f"{args.set}_pairs.parquet")
    queries = match.set_queries(args.set)
    y = match.pair_labels(s1, pool)
    keep = match.apply_decision(doc["decision"], s1, pool, np.asarray(p_cal, dtype=np.float32))
    scorer = match.Scorer(queries, s1, y, match.true_counts(queries))
    f_ent = scorer.per_entity(keep)[0]
    np.save(rd / f"{args.set}_per_entity.npy", f_ent)
    fa = np.load(match.runs_dir(args.parent) / f"{args.set}_per_entity.npy")
    assert len(fa) == len(queries), "reference scored on different queries"
    cmp = match.paired_delta(f_ent, fa, n_boot=2000)
    print(
        f"{args.set} F0.5: {args.parent}={fa.mean():.5f} {args.run}={f_ent.mean():.5f} "
        f"paired Δ={cmp['delta']:+.5f} [{cmp['ci95'][0]:+.5f}, {cmp['ci95'][1]:+.5f}] "
        f"n_changed={cmp['n_changed']} n={cmp['n']}"
    )
    io_utils.atomic_write_json(
        rd / f"confirm_{args.set}.json",
        {
            "run": args.run,
            "parent": args.parent,
            "set": args.set,
            "decision": doc["decision"],
            "f05_parent": float(fa.mean()),
            "f05_run": float(f_ent.mean()),
            "paired": cmp,
        },
    )


if __name__ == "__main__":
    main()
