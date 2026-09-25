# ML baseline report (numbers from artifacts/metrics/ml_oof.json, ml_baseline.json, ablation.json, loco.json)

Config: LightGBM (63 leaves, lr 0.05, 400 rounds, n_jobs 6) on 19 features
(name/addr lev-raw+norm, token Jaccard, TF-IDF char-ngram cosine, metaphone/soundex
set-Jaccard, token_set, postal-3-state, digit-Jaccard, country agree/unknown flags,
name/addr length diffs, rare-shared-token idf mass). No closed-set country encoding.
Candidates: ranked idf-union top-150 (blocking_report.md). TF-IDF fit on 500K pool
sample (unsupervised). Threshold/calibration: 5-fold GroupKFold-by-entity OOF on
60K-entity fit-sample; isotonic on OOF; t maximizing macro-F0.5 (R1) on OOF.

## Weighting

- Uniform vs hard-negative upweighting (negatives with name token_set>=0.7 x3):
  3-fold screen OOF R1 F0.5 = UNIFORM 0.9063 vs HARDx3 0.9050.
- Verdict: upweighting did not help (-0.0013); winner = uniform. (Negative result.)

## OOF (fit-sample, 5-fold)

- R1 t=0.62: F0.5=0.9052. R3 (t2=0.64): 0.9053 (+0.0001, negligible).
- OOF threshold curve: artifacts/metrics/ml_oof.json.

## Validation (full val, 441363 entities, applied once)

PENDING eval_val run.

## Decision rules

PENDING (R1/R2/R3 + R4 variants, singleton split, val-optimal-t reference).

## Ablation (drop-one-feature retrains, 15K-entity subsample, 30K val subset, fixed t)

PENDING ablation.json.

## LOCO (fit-A -> full val-B, both directions)

PENDING loco.json.

## Consolidation

PENDING multi-claim counts + R4 effect.

## Recommended feature set + rule + threshold

PENDING (from val numbers).
