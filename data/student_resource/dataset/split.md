# S1 train / validation split

Files live next to the original train TSVs:

`data/student_resource/dataset/train/`

## What was split

Only **S1** (queries) and the matching **ground-truth** rows.

| File | Role |
|---|---|
| `train_source1.tsv` | original full train S1 (unchanged) |
| `train_source1_train.tsv` | 1,765,458 S1 rows you may use labels from |
| `train_source1_validation.tsv` | 441,363 S1 rows for scoring only |
| `train_ground_truth.tsv` | original full train labels (unchanged) |
| `train_ground_truth_train.tsv` | labels for the train S1 rows |
| `train_ground_truth_validation.tsv` | labels for the validation S1 rows; scoring only |
| `train_source2.tsv` | full S2 pool — do not subset |
| `train_source3.tsv` | full S3 pool — do not subset |
| `s1_split_manifest.json` | seed, counts, country and singleton rates |

Official **test** files under `dataset/test/` are a different split (they include France). Do not score or tune on test labels.

## How the 20% was drawn

- Seed **42**.
- Each S1 row is **singleton** if `matched_entity_ids` is empty, else **matched**.
- Four strata: US matched, US singleton, India matched, India singleton.
- In each stratum, shuffle, take `round(20%)` to validation, rest to train.
- Same sizes as the existing EDA split: train 1,765,458 / validation 441,363.
- Singleton rate is ~5.585% on both sides. US/India shares match.

Rebuild: `python3 data/write_s1_split.py` from the workspace root (`amazon_ml`).

## Rules for anyone using this data

1. **Blocking and retrieval search all of S2 and S3**, for both train S1 and validation S1. Do not drop pool rows that are true matches of validation S1.
2. **Train S1 ground truth** may be used to set thresholds, mine negatives, and train models.
3. **Validation S1 ground truth** is only for scoring (per-S1 F0.5 over all validation S1 rows; empty prediction on a singleton is 1.0).
4. Do not use validation labels to pick a threshold, a model, or a design.
5. Unsupervised pool stats (token counts, abbreviation mining on S2/S3 text) may use the full S2+S3 files.
