# Amazon ML Challenge — business entity resolution

Match each S1 business record to its duplicates in the S2 + S3 pool. Three stages: inverted-index
blocking → LightGBM candidate re-ranker + cut (`candidate_pairs.tsv`) → LightGBM pair matcher with a
per-S1 decision rule (`matching_results.tsv`). Headline metric: per-S1-entity F0.5, macro-averaged
(rules in `AGENTS.md`).

Start here: `AGENTS.md` (rules) → `RESEARCH_LOG.md` (current best, open questions, every run) →
`submission/code/business_entity_resolution/README.md` (how to run).

## Layout

```
AGENTS.md, PROGRESS.md, RESEARCH_LOG.md   rules, phase log, experiment log
submission/
  code/business_entity_resolution/        the pipeline (package `ber`, configs/, tests/, run_matcher.sh)
  output/*.tsv                            submission 1 test outputs (Git LFS)
  Documentation_template.md               contest write-up
work/                                     pipeline intermediates (git-ignored), except trained models:
  stage1/model_v1.json                      stage-1 logistic blocking model
  rerank/model_v1.txt (+ meta, cut_v1.json) stage-2 LightGBM re-ranker (Git LFS)
  match/models/                             stage-3 matcher, run x1_strsim, 68 features, 5 folds (Git LFS)
  match_k5_submission1/models/              stage-3 matcher of submission 1, 50 features (Git LFS)
artifacts/metrics/*.json                  every reported number is written here by a script
plan/                                     design docs (BUCKETING_PLAN, MATCHER_PLAN, VALIDATION_PLAN,
                                          EXPERIMENT_ROUTINE, FEATURE_EXPERIMENTS), checks/, critique/, reference/
reports/                                  EDA, blocking, diagnostics, licenses, match error samples
notes/                                    problem statement and early notes
data/write_s1_split.py                    rebuilds the train/validation S1 split (TSVs not in git)
docs/split.md                             pointer to the split write-up
legacy/src/                               phase 0–3 scripts (EDA, first blocking + TF-IDF baseline); superseded by `ber`
archive/agent_runs/                       retired overnight-agent prompts, logs and tooling
```

## Which model is which

| Files | Run | Features | OOF F0.5 (MATCH_TRAIN) | MATCH_VALID F0.5 | Metrics |
|---|---|---|---|---|---|
| `work/match_k5_submission1/models/` | submission 1 (produced `submission/output/*.tsv`, commit `fd77ee7`) | 50 | 0.97412 | 0.97449 | `match_eval_MATCH_VALID.json` at commit `fd77ee7` |
| `work/match/models/` | x1_strsim (current code at HEAD) | 68 | 0.97807 | 0.97848 | `match_eval_MATCH_VALID_x1_strsim.json` |

`match-eval` refuses to load a `matcher.json` whose feature list differs from the code, so the
submission-1 models only load with the code at commit `fd77ee7`.

## Not in git

Contest TSVs (`student_resource/`, `data/student_resource/`), everything else under `work/` (~13 GB:
indexes, normalized stores, features, candidates), legacy `artifacts/*.parquet|*.pkl`, and zip bundles
(`*.zip`, `*.z01`). Rebuild `work/` with the commands in the package README.

Git LFS is required to fetch the models and output TSVs: `git lfs install && git lfs pull`.
