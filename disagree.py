"""NN-right/GBM-wrong and reverse, by segment (config E/F analysis).

Compares per-entity F0.5 of run B (NN_B scores on MATCH_TRAIN with its TRAIN-calibrated
decision) vs run A (M027 OOF per-entity) on MATCH_TRAIN queries.

Usage: python disagree.py  (from amazon_ml_challenge/)
Caveat: B's decision was tuned on MATCH_TRAIN, so B is slightly optimistic here;
M027 is OOF. This is a direction analysis, not a gate measurement.
"""

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
from ber import evaluate, io_utils, match  # noqa: E402


def main():
    nn_dir = match.runs_dir("NN_B")
    nn_matcher = io_utils.read_json(nn_dir / "models" / "matcher.json")
    t = pd.read_parquet(nn_dir / "MATCH_TRAIN_pairs.parquet")
    s, pool, p = (t[c].to_numpy() for c in ("s1_idx", "pool_idx", "p"))
    queries = match.set_queries("MATCH_TRAIN")
    y = match.pair_labels(s, pool)
    keep_b = match.apply_decision(nn_matcher["decision"], s, pool, p.astype(np.float32))
    scorer = match.Scorer(queries, s, y, match.true_counts(queries))
    fb = scorer.per_entity(keep_b)[0]

    m27 = match.runs_dir("M027")
    fa = np.load(m27 / "OOF_per_entity.npy")
    qa = np.load(m27 / "queries.npy")
    assert np.array_equal(qa, queries)
    print(
        f"M027 OOF F0.5 on MATCH_TRAIN: {fa.mean():.5f} | NN_B (TRAIN-calibrated): {fb.mean():.5f}"
    )

    masks = dict(evaluate.segment_data(queries, np.zeros(0, dtype=np.uint32))["query"])
    masks["singleton"] = match.true_counts(queries) == 0
    d = fb - fa
    for name, headline in (("nn_right", d > 0), ("gbm_right", d < 0)):
        sub = d[headline]
        print(
            f"\n{name}: n={headline.sum()} ({headline.mean() * 100:.2f}%), "
            f"mean|Δ|={np.abs(sub).mean():.4f}"
        )
        rows = []
        for seg, m in masks.items():
            both = m & headline
            if both.any():
                rows.append(
                    (
                        seg,
                        int(m.sum()),
                        int(both.sum()),
                        float(np.abs(d[both]).mean()),
                        float(d[m].mean()),
                    )
                )
        rows.sort(key=lambda r: -r[3])
        for seg, n_seg, n_both, mean_abs, mean_d in rows:
            print(
                f"  {seg:16s} seg_n={n_seg:6d} n={n_both:5d} ({n_both / n_seg * 100:5.2f}%) "
                f"mean|Δ|={mean_abs:.4f} seg_mean_Δ={mean_d:+.5f}"
            )


if __name__ == "__main__":
    main()
