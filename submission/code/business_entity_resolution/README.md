# Business Entity Resolution: reproduction guide

Pipeline: raw TSVs → text normalization → inverted-index blocking (stage 1) → LightGBM candidate
re-ranker + cut (stage 2, = `candidate_pairs.tsv`) → LightGBM pair matcher with calibrated
per-S1 decision (stage 3, = `matching_results.tsv`).

Design documents: `plan/BUCKETING_PLAN.md` (stages 1–2) and `plan/MATCHER_PLAN.md` (stage 3) in the
repository. Every reported number is written by a command into `artifacts/metrics/*.json`.

## 1. Environment

- Python 3.12 or newer (developed on 3.14.5, macOS arm64). The code only uses spawn-safe
  multiprocessing, so it also runs on Linux/WSL2 and Windows.
- `python -m venv .venv && .venv/bin/pip install -r submission/code/business_entity_resolution/requirements.txt`
- Libraries: numpy, pandas, pyarrow, rapidfuzz (MIT), jellyfish (MIT), scikit-learn (BSD-3),
  scipy, lightgbm (MIT), tqdm, matplotlib. No pretrained models. No network access is used at any step.

## 2. Layout and conventions

Run every command from the **repository root**, the folder that contains:

```
student_resource/dataset/{train,test}/*.tsv   contest data, unchanged (configs/paths.json: data_root)
work/                                         intermediate files, created by the pipeline
artifacts/metrics/                            metrics JSON written by every command
submission/code/business_entity_resolution/   this package
```

```bash
export PYTHONPATH=submission/code/business_entity_resolution/src
python -m ber.cli <command> [args]
```

`configs/blocking.json` holds the stage 1–2 settings, including values tuned by experiments E0–E6
(each recorded under `tuned_by`). `configs/match.json` holds the stage-3 settings. Worker count
defaults to `min(max_workers, cpu_count - 2)`.

## 3. Data split (fixed; see `student_resource/dataset/split.md`)

`splits` rebuilds the S1 train / validation split from the training ground truth: seed 42, strata
country × singleton, 20% to validation. It reproduces `data/write_s1_split.py` exactly. Train S1 is
then cut into disjoint work slices (seed 20260925):

| Slice | Used for |
|---|---|
| DEV_A, DEV_B | stage-1 tuning / confirmation |
| S1R_TRAIN | stage-1 logistic model |
| RR_TRAIN, RR_CAL | stage-2 re-ranker training / cut |
| MATCH_TRAIN (180,000) | stage-3 fit, calibration, decision rule (5-fold out-of-fold) |
| MATCH_VALID (20,000) | stage-3 confirmation, once |
| HOLDOUT_TEST = validation S1 (441,363) | headline score only, once per stage |

S2 and S3 are never split: every query searches the full pool. Validation-S1 labels are read only by
scoring commands (`rerank-eval --set HOLDOUT_TEST`, `match-eval --set HOLDOUT_TEST`).

## 4. Full reproduction (data → blocking → matching → output)

Times are measured on an 8-core M3 with 6 workers unless marked "est.".

| Step | Commands | Time |
|---|---|---|
| P1 ingest + split | `ingest --split train`; `ingest --split test`; `splits` | ~10 min (est.) |
| P2 normalization | `mine-abbrev --split train`; `normalize --split train --no-dict`; `learn-dict`; `normalize --split train` | ~45 min (est.) |
| P3 train index | `build-index --split train`; `index-sanity --split train` | 805 s |
| P4 stage-1 model | `stage1-train` | ~35 s |
| P5 stage-2 re-ranker | `rerank-build`; `rerank-train`; `rerank-cut` | build 169 s, train 69 s |
| P6 test side | `mine-abbrev --split test`; `normalize --split test`; `build-index --split test`; `index-sanity --split test` | ~15 min |
| P6 candidates | `candidates --set MATCH_TRAIN` (938 s); `candidates --set MATCH_VALID` (175 s); `rerank-eval --set HOLDOUT_TEST` (1,832 s, scores val-S1 once); `candidates --set TEST` (~2 h est.) | |
| P6 outputs | `write-outputs` (writes `work/outputs/candidate_pairs.tsv` + streaming validation); `monitor` | |
| Stage 3 | `bash submission/code/business_entity_resolution/run_matcher.sh` (section 5) | ~30 min (est.) |

The E0–E6 experiment commands (`abbrev-e0`, `s1-eval --exp ...`) are needed only to re-derive the
tuned values already stored in `configs/blocking.json`. `rerank-cut` re-derives the stored cut from
RR_CAL deterministically.

## 5. Stage 3: matcher

`run_matcher.sh` runs, in order:

| Step | Command | Output |
|---|---|---|
| M1 | `match-features --set MATCH_TRAIN` / `--set MATCH_VALID` | `work/match/features/<SET>/part-*.parquet` (no labels stored) |
| M2 | `match-train` | 5 fold models, isotonic calibration, decision rule → `work/match/models/`; `artifacts/metrics/match_train.json`; `reports/match_errors/*.csv` |
| M3 | `match-eval --set MATCH_VALID` | `artifacts/metrics/match_eval_MATCH_VALID.json` (confirmation; nothing is tuned on it) |
| M4 | `match-features --set TEST` | test features (inputs only) |
| M5 | `match-predict` | `work/outputs/matching_results.tsv` + format / subset check, `artifacts/metrics/match_predict_TEST.json` |
| M6 (once, by hand) | `match-eval --set HOLDOUT_TEST` | headline val-S1 F0.5 → `artifacts/metrics/match_eval_HOLDOUT_TEST.json`. It refuses to run twice unless `--force` is given |

What `match-train` does:

- It trains LightGBM (binary logloss, no class reweighting; the positive rate inside candidate lists is
  0.62) with GroupKFold by S1 (5 folds). Each fold early-stops on 10% of its own training S1.
- It fits isotonic calibration on the out-of-fold predictions.
- On the out-of-fold predictions it picks one decision rule:
  - a global threshold on calibrated p, or
  - per-S1 expected-F0.5-optimal top-k (exact, from Poisson-binomial distributions).
- Either rule can add the one-owner filter: a pool record is kept only for the S1 that gives it the
  highest p. This uses the ground-truth fact that no pool record has two owners, and reads only inputs.
- At inference it averages the 5 fold models and applies the stored calibration and rule.

Features (50): the stage-2 score and rank; name similarity on normalized text (rapidfuzz ratios,
Jaro-Winkler, IDF-weighted token overlap from pool document frequency, missing-rare-token IDF,
equality after removing data-mined edge tokens, acronym, consonant skeleton); address similarity
and number agreement (house number, shared / conflicting numbers of ≥ 3 digits, numeric Jaccard);
country same / different / unknown (no country one-hot); and list context per S1 (score gaps,
rank among the S1's candidates, how many candidates look alike). Missing information is NaN, never 0.

### Matcher only (e.g. on another machine)

Copy the repository and create the venv. Then copy these bucketing outputs into `work/`, keeping the
same paths (about 3.8 GB, plus `candidates/TEST` once it exists):

```
work/candidates/{MATCH_TRAIN,MATCH_VALID,HOLDOUT_TEST,TEST}/
work/records/
work/norm/{train,test}_s1.parquet  work/norm/{train,test}_s1_chain.npy
work/norm/{train,test}_pool_store/
work/index/{train,test}/meta.json  work/index/{train,test}/{NT,AT}.*.npy
work/splits/
work/rerank/model_v1.txt  work/rerank/model_v1_meta.json
```

Also copy `student_resource/` (for validation). Then run `bash submission/code/business_entity_resolution/run_matcher.sh`.

A fingerprint of the stage-2 model and cut is stored with every feature set and with the trained
matcher. If the bucketing outputs change, `match-train`, `match-eval` and `match-predict` refuse to
run until features are rebuilt.

## 6. Packaging the submission

```bash
mkdir -p submission/output
cp work/outputs/candidate_pairs.tsv work/outputs/matching_results.tsv submission/output/
python student_resource/utils/validate_submission.py --matching submission/output/matching_results.tsv --test-dir student_resource/dataset/test
python submission/code/business_entity_resolution/src/ber/validate_stream.py --candidate submission/output/candidate_pairs.tsv --test-dir student_resource/dataset/test
```

The official validator also accepts `--candidate`, but it holds every candidate ID in Python sets,
which can take several GB of RAM. `validate_stream.py` applies the same rules to the candidate file
in a streaming pass.

## 7. Tests

```bash
cd submission/code/business_entity_resolution && PYTHONPATH=src python -m unittest discover -s tests
```
