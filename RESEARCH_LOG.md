# Research log

Lab notebook for every experiment: what we tried, what the number did, what we concluded.
Negative, flat, and failed runs are logged too — they are the part people forget and then re-run.

**Rules**

1. One entry per run or decision, **newest first**. Append; never rewrite an old entry. If a later run
   shows an entry was wrong, add a new entry that says so and link back (`see M007`).
2. Every number cites the `artifacts/metrics/*.json` that holds it (AGENTS rule 6). No file, no number.
   A run that crashed or was killed is logged as `FAILED` with the reason.
3. Prose is the point: hypothesis before the run, interpretation after. "Δ +0.0004" alone is not an entry.
4. Update **Current best** in the same edit as any `ADOPTED` entry.
5. IDs: `E0–E6` stage-1 blocking, `R*` stage 2, `M###` stage-3 matcher/feature runs
   (`exps/M###.json`, see `plan/EXPERIMENT_ROUTINE.md`), `N*` measurement-only, `S*` submissions.
6. `reports/experiments.md` (generated) is the table; this file is the narrative. PROGRESS.md tracks
   phases, not experiments.

**Entry template**

```
### YYYY-MM-DD · M### · <short title> · ADOPTED | PARKED | DROPPED | FAILED | INFO
- Parent: M### · Commit: <sha> · Metrics: artifacts/metrics/<file>.json · Wall: <min>
- Hypothesis: <pattern seen, in which file/tag count> → <feature/change> should move <metric> because <mechanism>.
- Change: <exact feature names / params / rule>.
- Result: F0.5 <parent> → <new>, paired Δ <x> [CI lo, hi]; fixed <n> / broken <n>; segments that moved.
  Error tags: <tag> FP <a>→<b>, FN <a>→<b>. Mini-lockbox (if adopted): <value>.
- Learned: <what this says about the data or model, including "no effect">.
- Next: <the follow-up this suggests, or "none">.
```

---

## Current best

| Stage | Set | Metric | Value | Entry | Metrics file |
|---|---|---|---|---|---|
| 1 blocking | DEV_B 10K | F0.5 ceiling | 0.99550 | E6 | `s1_E6.json` |
| 1+2 candidates | Val S1 441,363 | F0.5 ceiling / mean size | 0.99276 / 5.43 | R2 | `rerank_eval_HOLDOUT_TEST.json` |
| 3 matcher | MATCH_TRAIN 180K OOF | entity F0.5 | 0.97412 | M000 | `match_train.json` |
| 3 matcher | MATCH_VALID 20K | entity F0.5 | 0.97449 | M000 | `match_eval_MATCH_VALID.json` |
| 3 matcher | MATCH_TRAIN 180K OOF | entity F0.5 | 0.98107 (x1_strsim 0.97807; test-like Δ +0.00186) | M005 | `exp_M005.json`, `universe_owner_M005.json` |
| 3 matcher | MATCH_VALID 20K | entity F0.5 | 0.98162 | M005 | `match_valid_confirm_M005.json` |
| 3 matcher | MATCH_TRAIN 180K OOF | entity F0.5 | 0.98211 (comp + num) | M016 | `exp_M016.json` |
| 3 matcher | MATCH_ALL held-out 165K | entity F0.5 | 0.98360 (full_comp; full_single 0.98161 same S1) | M005-full | `match_train_full_comp.json` |
| submission | test (public LB) | entity F0.5 | 0.966797 (S2, full_single); S1 0.966109; S3 0.966 (rounded, worse) | S2 | `match_train_full_single.json`, `reports/test_usage_log.md` |

## Open questions

- Internal→leaderboard gap −0.0148 (S2). N03/N04 explain ~0.008 from list statistics; ~0.006 is not visible without labels. Plan: `plan/RCA_RESEARCH_PLAN.md`.
- Paired SE of a feature change at 180K. Unmeasured until the first M run (N01 only covers one-owner).
- How much the OOF score is inflated by `translit_dict` being mined from DICT_SRC labels (VALIDATION_PLAN P4). Unmeasured.

---

## Log

### 2026-09-27 · S6-file · full_ce: live features + cross-encoder p_ce group, MATCH_ALL minus DEV_REST_180K · INFO (upload candidate)
- Metrics: `match_train_full_ce.json` · Chain: `plan/checks/run_submission_ce.sh` (log `logs/run_submission_ce.log`) ·
  Wall: HF a100-large scoring MATCH_TRAIN + DEV_REST_REST 34 min (~$1.42; AUC MATCH_TRAIN 0.99838), train 564 s,
  exp-predict 297 s.
- Change: 68 live features + `p_ce_rec`, `p_ce_rec_rank`, `p_ce_rec_gap` (exp group `ce:ce_rec`). DEV_REST_180K rows
  dropped (cross-encoder training S1: p_ce in-sample there); same seeded fit / early-stop / calibration split as
  full_single, so the calibration slice is out-of-sample for both models.
- Result: best_iteration 2334/12000 (converged). Calibration slice 147,462 S1: full_ce 0.98537 vs full_single 0.98162,
  paired Δ +0.00375 [0.00348, 0.00401], 5,300 S1 changed. Decision: threshold 0.69 + one-owner.
- Test: 5,744,247 pairs (S2 5,789,591); 103,719 empty S1. File: `submission/output_v6/matching_results.tsv`
  (sha1 c33d044e…); official validator --check-ids PASS.
- Caveat: internal→LB transfer has failed before (S3). p_ce is a per-pair score, not a cross-list statistic like
  comp, so the S3 failure mode (train-vs-test list structure) should not apply — untested until the LB number.
- Next: upload; log the LB score as S6-LB.

### 2026-09-27 · CE-FEAT-smoke · p_ce group in the final trainer, 50-round smoke (MATCH_TRAIN + MATCH_VALID only) · INFO
- Metrics: `match_train_smoke_ce.json` · Script: `EXCLUDE_SETS=DEV_REST_180K,DEV_REST_REST NUM_BOOST_ROUND=50
  train_final_comp.py smoke_ce ce:ce_rec` · Wall: 25 s train, 48 s exp-predict on TEST · Model deleted after the check.
- Purpose: exercise the new EXCLUDE_SETS / `ce:` group path end to end before the full run (not a candidate).
- Result: calibration slice 19,985 S1 (same seeded split as full_single, so out-of-sample for both):
  smoke 0.98383 vs full_single 0.98256, Δ +0.00127 [0.00045, 0.00213]; truncated by design (50/50 rounds).
  p_ce joins 100% of feature rows; standalone AUC MATCH_VALID p_ce 0.99841 vs p_rerank 0.98605.
- Next: full run `full_ce` on MATCH_ALL minus DEV_REST_180K (plan/checks/run_submission_ce.sh).

### 2026-09-27 · S5-file · Cross-encoder only (LoRA bge-reranker-v2-m3, ce_rec), threshold + one-owner · INFO
- Metrics: `ce_submit_ce_rec.json` · Scripts: `ce/hf_job/score_job.py` (HF Jobs a100-large, 49 min, ~$2.05),
  `ce/hf_job/collect.py`, `ce/ce_submit.py submit --ce ce_rec --fit-set MATCH_TRAIN_S20000` · Adapter: Friend B's
  1-epoch LoRA on DEV_REST_180K (branch submission-v3, `cross_encoder_lora/adapter/`).
- Scoring: bf16 on A100, ~3,700 pairs/s; 10,613,056 TEST pairs, 0 non-finite. Format gate: AUC MATCH_VALID 0.99841,
  MATCH_TRAIN_S20000 0.99835 (friend's held-out eval 0.9986). Local M3 MPS fp32 measured 76 pairs/s (not viable).
- Decision (fitted on 20,000 train S1, never on test): p_ce >= 0.79 + one-owner; fit F0.5 0.97650.
  MATCH_VALID (scoring only) F0.5 0.97552 — below M005 on MATCH_VALID (0.98162), above M000 (0.97449).
- Test: 5,637,038 pairs; ~3.2 predicted per S1 and ~6% empty in every country (France, India, US).
  File: `submission/output_v5/matching_results.tsv` (sha1 663f29bf…); official validator --check-ids PASS.
- Expectation: below S2 (0.966797) on the LB; uploaded as a standalone read of the cross-encoder.
- Next: p_ce as a LightGBM feature (MATCH_ALL minus DEV_REST_180K, where p_ce would be in-sample).

### 2026-09-27 · S4-file · comp + num on MATCH_ALL, hybrid file (diagnostic upload candidate) · INFO
- Metrics: `match_train_full_comp_num.json`, `final_hybrid_full_comp_num.json` · Scripts: `train_final_comp.py full_comp_num comp num`,
  `final_hybrid.py full_comp_num` · Wall: 33.5 min train + ~50 min files
- Result: best_iteration 5636/12000 (converged). Calibration slice: full_comp_num 0.98448 vs full_single 0.98161
  (+0.00287 [0.00263, 0.00310]); hybrid (threshold 0.64) 0.98324, +0.00163 [0.00145, 0.00179]. Test: hybrid
  5,817,998 pairs (S2 5,789,591; S3 5,827,052); official validator --check-ids PASS.
  File: `submission/output_v4/matching_results.tsv` (copy of work/outputs/full_comp_num_hybrid/).
- Caveat: S3 (same method without num) scored below S2 on the LB; num failed US→India LOCO (−0.00450). Upload
  only as an A/B diagnostic against S3, not as an expected improvement.

### 2026-09-26 · S3-LB · Submission 3 leaderboard: contention hybrid did not transfer · INFO
- Log: `reports/test_usage_log.md` (upload 23:05) · Model metrics: `final_hybrid.json`, `match_train_full_comp.json`
- Result: public LB shown as 0.966 (rounded, exact pending) vs S2 0.966797 — between −0.0003 and −0.0013, against
  an internal held-out gain of +0.00143 (hybrid) on the MATCH_ALL calibration slice.
- Learned: third internal→LB failure (S2 kept ~10%, S3 negative). Candidates: (1) contention distribution
  shift on contested rows (N07: test US/IN less contested, France 1.17 vs 0.46 mean log lists-per-record);
  (2) hybrid threshold 0.59 vs live 0.69 added 37,461 pairs on test (unmeasured whether FP);
  (3) internal validation does not reproduce the test pool's structure (4.68 vs 5.75 records per S1), so any
  cross-list feature is tuned to train's structure. Internal gains from cross-list features are not evidence
  for the leaderboard until a test-like validation set (RCA D3) exists.
- Next: do not upload the comp+num file; build the D3 densified validation set; re-judge M005/M010/M017 on it.

### 2026-09-26 · N08 · LOCO by feature group (item 14, France proxy) · INFO
- Metrics: `loco_groups.json` · Script: `plan/checks/loco_groups.py` · Wall: ~50 min (paused 8 min for the S3 deadline)
- Change: one LightGBM per direction on one country's MATCH_TRAIN S1 (90% fit / 10% early stop + isotonic),
  x1 threshold 0.67 + one-owner, scored on the other country; paired vs the 68-feature base.
- Result (US→India / India→US): base 0.95268 / 0.97216. +comp +0.00497 / +0.00506; +num −0.00450 / +0.00151;
  +sib +0.00131 / −0.00144; +dinv +0.00045 / +0.00021. Dropping: name_str +0.00039 / −0.00181, idf −0.00720 /
  −0.00274, addr_str −0.01234 / −0.00862, list −0.00062 / −0.00158, counts −0.00077 / −0.00184, context
  (src, country3, pool_indic) +0.00081 / −0.00005. All CIs in the file.
- Learned: contention transfers across countries; the address-number group is country-specific (US-trained
  number rules hurt India). No base family is dead weight except possibly `context` for US→India.
- Next: prefer comp-only for France-heavy uncertainty; if num is kept, consider it only with India+US training
  (already the case) and watch the S3 vs S4 leaderboard difference.

### 2026-09-26 · M017 · Specialists (converged, cap 10000) on top of comp + num · PARKED (needs canary + full-scale plan)
- Parent: M016 · Metrics: `exp_M017.json` · Wall: ~70 min (concurrent jobs)
- Result: OOF 0.98330 vs 0.98211, Δ +0.00119 [0.00098, 0.00141]; band +0.00424; singleton −0.00010 [−0.00196, 0.00186].
  Name specialist converged at 4056-4732/10000; no fold truncated.
- Learned: the specialist/disagreement stack is additive with comp + num. Stacked features need the label-shuffle
  canary (EXPERIMENT_ROUTINE §6) and 5-fold specialist OOF on MATCH_ALL (several hours) before a submission.
- Next: canary on MATCH_TRAIN, then plan the MATCH_ALL stack.

### 2026-09-26 · M015 · Fellegi-Sunter m/u log-likelihood feature (item 12) · DROPPED
- Parent: x1_strsim · Metrics: `exp_M015.json`
- Result: OOF 0.97813, Δ +0.00007 [−0.00008, 0.00022]; band +0.00025 (CI crosses 0).
- Learned: trees already read the same binned agreement pattern from the raw columns.

### 2026-09-26 · S3 · Submission 3 file (comp-only hybrid) · INFO
- Metrics: `final_hybrid.json`, `match_train_full_comp.json` · File: `submission/output_v3/matching_results.tsv`
  (sha1 b84e9e5e…, copy of work/outputs/full_hybrid/)
- Rule: rows whose pool record is in >= 2 test S1 lists take full_comp's p, others full_single's; threshold 0.59,
  one-owner off (chosen on the MATCH_ALL calibration slice). Slice: hybrid 0.98305, full_comp 0.98360, full_single
  0.98161; hybrid − single +0.00143 [0.00125, 0.00160].
- Test: 5,827,052 pairs (submission 2: 5,789,591); contested row share 32.1%; official validate_submission.py
  --check-ids PASS (also PASS for the pure full_comp file). Leaderboard score: pending upload.

### 2026-09-26 · N08 · FP/FN report with raw text, full_single + full_comp, MATCH_ALL calibration slice · INFO
- Parent: none · Metrics: `error_report.json`, `error_report_tags.json` · Wall: 27 min (feature load)
- Hypothesis: none (measurement, asked by the team). Rows: 165,545 train S1 held out from both final models.
- Result: F0.5 reproduced (full_single 0.98161, full_comp 0.98360). full_comp errors: FP 1,648, FN (in list)
  9,928, FN_MISSED (true link never in the candidate list) 14,037. Loss (sum of 1 − per-S1 F0.5 = 2,714) by
  error type per S1: FN_MISSED only 1,130 (42%), FN only 971 (36%), FP only 378 (14%), mixed 234.
  FN in list: 63% pool address empty, 54% name token-set ≥ 95, median p_cal 0.297. FN_MISSED: 59% India,
  26% name token-set < 50, 23% non-Latin text. FP: median p_cal 0.867, 23% disjoint address numbers, 39% name ≥ 95.
- Learned: candidate generation (FN_MISSED) is the largest single loss source on this slice, ~0.0068 F0.5,
  larger than the stage-1 share measured on DEV_B (0.0045, `s1_E6.json`). Not yet split into stage-1 miss vs
  stage-2 cut (K_max 60 / p_min 0.05).
- Next: split FN_MISSED by stage; bi-encoder kNN retrieval channel targets the name<50 / non-Latin part.
  Files: `work/reports/errors/errors_{full_single,full_comp}.parquet`.

### 2026-09-26 · M016 · comp + num combined · ADOPTED
- Parent: M005 · Metrics: `exp_M016.json` · Wall: 15 min (with a concurrent full-data job)
- Result: OOF 0.98211 vs M005 0.98107, Δ +0.00104 [0.00085, 0.00124]; band +0.00368 [0.00302, 0.00439]; singleton
  +0.00098 [−0.00078, 0.00255]. vs x1_strsim +0.00404 (separately +0.00300 and +0.00132: close to additive).
  No fold truncated.
- Next: full_comp_num on MATCH_ALL + hybrid files (`train_final_comp.py full_comp_num comp num`, `final_hybrid.py full_comp_num`).

### 2026-09-26 · M005-full · full_comp: live recipe + comp on MATCH_ALL · INFO (submission-3 candidate)
- Metrics: `match_train_full_comp.json` · Script: `plan/checks/train_final_comp.py` · Wall: 46.7 min
- Change: train_final_single.py unchanged (same seeded fit / early-stop / calibration split, params, cap 12000) plus
  the `comp` group; saved to `work/match/runs/full_comp/models/`, NOT copied to the live dir.
- Result: best_iteration 6524/12000 (converged). Held-out calibration slice (165,545 S1): 0.98360 vs full_single
  0.98161 on the same S1, Δ +0.00199 [0.00178, 0.00220]. Decision: threshold 0.67, one-owner off.
- Learned: the 180K gain carries to full scale at ~2/3 size. full_single's slice score has only slice-level
  one-owner, so part of the Δ is the one-owner coverage gap that test already closes (N05b: ~+0.0009).
- Next: `final_hybrid.py` (contested-only hybrid, N07) and test files.

### 2026-09-26 · N07 · M005 sensitivity to contention density; contested-only hybrid · INFO
- Metrics: `comp_density_check.json` (script `plan/checks/comp_density_check.py`); hybrid and bucket counts ad-hoc from
  `work/match/runs/{x1_strsim,M005}/oof.parquet` + `work/exp/groups/MATCH_TRAIN/comp.parquet` (no metrics file:
  numbers below are to be regenerated by `plan/checks/final_hybrid.py` on the MATCH_ALL slice before use).
- Hypothesis: test US/India rows are LESS contested than train (mean c_log_n_own 0.26 / 0.32 vs 0.46 train; France
  1.17), because the test pool adds unclaimed records. M005 learned contention at train density.
- Result: thinning the other S1 lists to 50% (mean 0.318) makes M005 −0.00229 [−0.00260, −0.00198] vs x1_strsim;
  25%: −0.00689. (Pessimistic: thinning also removes true owners, which test does not.) On M005 OOF, contested
  rows: FP 2280→869, TP +180; uncontested rows: FP 1376→1616, TP +2549 — M005 loosens uncontested rows.
  Hybrid (M005 p on contested rows, x1_strsim p on uncontested, one threshold 0.66 + one-owner): Δ +0.00213
  [0.00194, 0.00232] vs x1_strsim, band +0.00729 (M005 alone +0.00300).
- Learned: the contested-row gain is the robust part; the uncontested-row gain depends on train's orphan density.
- Next: submission 3 as the hybrid of full_comp (contested) and full_single (uncontested); pure full_comp as the
  alternative file.

### 2026-09-26 · M014 · 3-seed LightGBM average (item 17) · PARKED
- Parent: x1_strsim · Metrics: `exp_M014.json` · Wall: ~20 min
- Result: OOF 0.97824, Δ +0.00018 [0.00006, 0.00029]; band +0.00072 [0.00027, 0.00119]; singleton 0.0. No fold truncated.
- Learned: variance reduction is real but small; at MATCH_ALL scale it triples training time (~3 x 35 min).
- Next: only as a final add-on if time allows.

### 2026-09-26 · M013 · Residual LightGBM on the parent's uncertain band (item 10) · PARKED
- Parent: x1_strsim · Metrics: `exp_M013.json` · Wall: 20 s (band rows only)
- Change: second model on rows with x1_strsim OOF p_cal in [0.1, 0.9) (25% of S1), features + parent raw p
  (`par_p`), own isotonic on the band; other rows keep the parent's p.
- Result: OOF 0.97840, Δ +0.00033 [0.00017, 0.00049]; band +0.00131; India +0.00066, US +0.00011 (CI crosses 0).
  Folds converge at <= 152 rounds.
- Learned: a band specialist adds little over one model that already sees every row; the band loss is
  information-limited (M008 said the same). Below the +0.0005 minimum gain.
- Next: retry on top of the adopted feature set only if cheap.

### 2026-09-26 · M012 · One LightGBM per pool source S2 / S3 (items 8, 13) · DROPPED
- Parent: x1_strsim · Metrics: `exp_M012.json` · Wall: 7 min
- Result: OOF 0.97694, Δ −0.00113 [−0.00131, −0.00094]; band −0.00423; every segment worse.
- Learned: splitting halves the data per model; `src` as a split feature already captures source-specific noise.
- Next: none.

### 2026-09-26 · M011 · Name / address / context specialists stacked + disagreement (items 9, 11) · PARKED (truncated)
- Parent: x1_strsim · Metrics: `exp_M011.json` · Wall: ~20 min
- Change: three LightGBMs on name-only (n_*), address-only (a_*), context-only (p_rerank, rank, l_*, src, country3,
  pool_indic, log_chain) columns, 5-fold OOF on the same folds; sp_name, sp_addr, sp_ctx, sp_name_minus_addr stacked
  into the main model (test time: fold average).
- Result: OOF 0.97981, Δ +0.00174 [0.00149, 0.00199]; band +0.00686; India +0.00233, US +0.00134. The name
  specialist hit the 3000 cap in all 5 folds (2989-3000) — its OOF is under-trained, so this number is not the
  converged result. Main model converged at 625-793. Label-shuffle canary for stacked features not yet run.
- Learned: the disagreement/stacking signal is real at this size, but the run is not a clean measurement.
- Next: re-run with a specialist cap >= 8000, plus the canary, then combine with comp + num.

### 2026-09-26 · M010 · Structured address-number group (item 7) · ADOPTED (for combination)
- Parent: x1_strsim · Metrics: `exp_M010.json` · Wall: 8 min
- Change: group `num`: first address number equal / digit-dropped / different (nm_first_state) and log distance,
  any digit-drop pair, postal-like (>=5 digits) and unit-number agreement, number counts, shared numbers in the
  same order. Country-agnostic, no labels.
- Result: OOF 0.97939, Δ +0.00132 [0.00112, 0.00151]; band +0.00497; US +0.00146, India +0.00112, singleton
  +0.00333. nm_first_logdiff gain rank 7, nm_first_state 9. Folds <= 1978/3000.
- Learned: "first number" vs "any number" agreement and the numeric distance separate house-number conflicts that
  a_num_jacc and a_house miss. (X2's regex version measured +0.00047; this one is ~3x.)
- Next: M016 = comp + num.

### 2026-09-26 · M005 · Pool-side contention features (reverse retrieval, items 1/4/5) · ADOPTED
- Parent: x1_strsim · Metrics: `exp_M005.json`, `universe_owner_M005.json`, `match_valid_confirm_M005.json` · Wall: 6.3 min
- Hypothesis: N05 — FP rows are mostly records another S1 owns; in-band rows beaten by another S1's p_rerank by
  >=0.2 match 11% vs p_cal 0.28. Features on how each pool record is contested across ALL S1 candidate lists
  (train side: every train-split S1 with candidates incl. validation-S1 inputs, no labels; test side: all test S1).
- Change: group `comp` (`src/ber/exp.py`): c_log_n_own, c_rank_q, c_margin (own p_rerank − best other S1's),
  c_n_other_ge05, c_best_other, c_q_share_not_best, c_q_share_lose02. 75 features.
- Result: OOF 0.98107 vs 0.97807, Δ +0.00300 [0.00274, 0.00324]; band S1 +0.01115 [0.01020, 0.01208]; US +0.00261,
  India +0.00359, singleton +0.00422. Test-like decision (one-owner over all train S1 for both runs, competitors =
  full_single in-sample p): Δ +0.00186 [0.00162, 0.00208] (re-swept thresholds +0.00174); band +0.00750, non-band
  −0.00003 [−0.00013, 0.00005]. MATCH_VALID (once): 0.98162 vs 0.97848, Δ +0.00313 [0.00242, 0.00384].
  Gain ranks: c_margin 4, c_best_other 5, c_rank_q 13. Folds 1200-1758/3000, none truncated. One-owner no
  longer chosen (the features subsume it).
- Learned: about 60% of the gain is information one-owner cannot give (a soft, learned version of contention plus
  its interaction with list features); all of it sits in band S1, which is 35-57% of test S1 vs 21% of train.
  Test coverage of the signal matches train (32.1% vs 33.6% contested rows).
- Next: retrain with `comp` on MATCH_ALL (1.65M S1, cap >= 12000 per ROUND_CAP_EVIDENCE) for submission 3.

### 2026-09-26 · N07 · Kaggle T4 throughput probe for cross-encoder ce_rec_base (bge-reranker-base, full FT) · INFO
- Parent: none · Metrics: `ce_rec_base_probe_k0.json`, `ce_pairs_manifest.json` · Wall: 4 min on Kaggle 2×T4
- Hypothesis: a 278M cross-encoder full fine-tune plus scoring of MATCH_TRAIN/VALID/TEST fits in the free
  Kaggle quota (30.00 GPU-h/week, measured with `kaggle quota`).
- Change: none (measurement). Pair files: 5 sets, row counts equal to the feature tables, S1 overlap of
  DEV_REST_180K with MATCH_TRAIN / MATCH_VALID / DEV_REST_REST / HOLDOUT_TEST = 0.
- Result: one T4 trains at 193 pairs/s (batch 64, max_length 128, fp16 autocast, peak VRAM 7.5 GB) and scores
  at 1,623 pairs/s (1,190–1,390 including tokenization). Projected: 1 epoch 1.33 h, MATCH sets 0.09 h,
  TEST 0.91 h, DEV_REST_REST 0.59 h. Untrained bge-reranker-base ROC-AUC on 20k MATCH_VALID pairs 0.8365.
  Toy run (2,873 pairs, 30 steps): held-out AUC 0.817 → 0.924. All code paths (train save, 2-GPU shard
  scoring, merge) ran on Kaggle.
- Learned: the cost concern was unfounded at 278M: ~2.5 GPU-h total. Kaggle image: torch 2.10.0+cu128,
  transformers 5.0.0.
- Next: k2 (1 epoch + scoring) running; then `ce/evaluate.py` and an M run with group `ce:ce_rec_base`.

### 2026-09-26 · M009 · Copy-cluster support + S2/S3 triangulation, text only (items 5, 6) · DROPPED
- Parent: x1_strsim · Metrics: `exp_M009.json` · Wall: 7 min (group build 13 s)
- Hypothesis: true matches of one S1 are near-duplicates of each other (sb_n_dup 2.28 for y=1 vs 1.14 for y=0 on
  3,000 S1); candidate-to-candidate name/address token-set (>=90 / >=80) without X3's stacked pass-1 p.
- Result: OOF 0.97825, Δ +0.00018 [0.00001, 0.00036]; band +0.00071 [−0.00001, 0.00147]; singleton −0.00255
  [−0.00427, −0.00078] (guard breach). Best column sb_best_addr_sim gain rank 9. Folds 1650-2134/3000.
- Learned: X3's singleton failure is not only from stacking; any "my candidates agree with each other" evidence
  raises p for chain duplicates in singleton lists too. Small gain, same failure mode.
- Next: none unless combined with a candidate-to-S1 gate.

### 2026-09-26 · M008 · Upweight feature-ambiguous pairs x2 (hard-negative curriculum, item 3) · DROPPED
- Parent: x1_strsim · Metrics: `exp_M008.json` · Wall: 7 min
- Hypothesis: 56% of loss sits in band S1; doubling the weight of pairs that look ambiguous from features alone
  (n_tset>=0.9 with a_tset<0.6 or empty, or |gap to next p_rerank|<0.1 with p_rerank in [0.05,0.95]; 18.5% of rows,
  58% of band rows) should spend more splits there. (First spec used 0-100 thresholds on 0-1 columns and was
  fixed before the run.)
- Result: OOF 0.97792, Δ −0.00015 [−0.00029, −0.000004]; band S1 −0.00064 [−0.00120, −0.00003]. Folds 2168-2411/3000.
- Learned: reweighting by a feature rule moves splits away from rows the model already separates without helping
  the ambiguous ones; the band loss is information-limited, not attention-limited.
- Next: none.

### 2026-09-26 · M007 · Macro-aware S1 weighting 1/n_candidates (item 1) · DROPPED
- Parent: x1_strsim · Metrics: `exp_M007.json` · Wall: 6.5 min
- Hypothesis: logloss averages over pairs, the metric over S1; weight 1/n makes each S1 count once.
- Result: OOF 0.97817, Δ +0.00010 [−0.00011, 0.00031]; band +0.00038 [−0.00049, 0.00126]; singleton segment
  −0.0149 [−0.0175, −0.0126] (guard breach). Decision flipped to expected-F.
- Learned: singleton lists are short, so 1/n upweights them as rows but the decision then loses singletons; the
  overall effect is noise. Guard failure alone rejects it.
- Next: none.

### 2026-09-26 · M006 · Density-invariant list features (item 2, RCA M3) · PARKED
- Parent: x1_strsim · Metrics: `exp_M006.json` · Wall: 7 min
- Hypothesis: l_n / count list features scale with pool density (test denser); z-scores and shares within the list
  (d_prr_z, d_rank_frac, d_share_prr05, d_prr_minus_med, d_share_prr_close, d_ntset_z, d_atset_z, d_nidf_z) carry the
  same ordering in a density-free form.
- Result: OOF 0.97796, Δ −0.00011 [−0.00028, 0.00005]; band −0.00044 [−0.00103, 0.00018]. Folds 1528-1990/3000.
- Learned: no in-distribution gain; OOF cannot show the density benefit it targets. Checked for transfer in
  `loco_groups.json` (+dinv) instead.
- Next: LOCO diagnostic.

### 2026-09-26 · N06 · Decision variants: threshold surface (item 16), calibration variants (item 19) · INFO
- Metrics: `decision_variants_x1_strsim.json` · Script: `plan/checks/decision_variants.py` · Wall: ~6 min, no training
- Hypothesis: one global isotonic map and one threshold may be wrong for long or tied lists (N04 hinted +0.00019).
- Change: on x1_strsim OOF, everything cross-fitted over the 5 folds (fit on 4, apply to 1), one-owner in all.
  A global isotonic + threshold; B isotonic per list-size bucket; C Platt; D threshold per list-size bucket;
  E threshold per (list-size bucket x top-2 p_rerank gap < 0.1).
- Result: A 0.97788. B +0.00003 [−0.00002, 0.00008]; C +0.00002 [−0.00003, 0.00007]; D +0.00007 [0.00003, 0.00011];
  E +0.00016 [0.00004, 0.00029], band S1 +0.00064.
- Learned: calibration variants do nothing. A 2-D threshold surface is a small real gain concentrated in band S1.
  Test has more long/tied lists, so the surface would fire more often there (c).
- Next: re-run on the final parent; if E still holds, add a per-cell threshold to the decision rule.

### 2026-09-26 · R0 · Experiment runner reproduces x1_strsim · INFO
- Metrics: `exp_R0.json` · Code: `src/ber/exp.py` (`exp-train`, `exp-predict`) · Wall: 6.5 min
- Change: new runner that writes only to `work/match/runs/<id>/` (match-train --run also overwrites the live model),
  with feature groups, label-free sample weights, seeds, band-stratum paired delta.
- Result: OOF 0.97807, per-entity max |diff| vs x1_strsim 0.0; best_iteration 1651/1819/2011/1908/1574 = x1_strsim.
- Next: M005-M009.

### 2026-09-26 · N05b · Pool-competition rule on top of universe one-owner · DROPPED
- Metrics: `pool_competition_increment.json` · Script: `plan/checks/pool_competition_increment.py` · Wall: 55 min
- Hypothesis: N05's +0.00104 compared against one-owner that only saw the 165,545-S1 slice. Test-time match-predict
  runs one-owner over all 1.73M test S1, so the rule may already be in the submission.
- Change: competitors' p_cal = full_single on every train feature row (in-sample outside the slice, so one-owner here
  is optimistic); rule applied only on rows whose pool record is in no HOLDOUT_TEST/DEV_B list (84.1% of rows).
- Result: universe one-owner vs none +0.00094 [0.00085, 0.00103]. p_rerank rule on top: m=0 −0.00005
  [−0.00009, −0.00002] (316 rows dropped, 247 of them true); m=0.2 −0.00001 [−0.00003, 0.00001]. Test replay of the
  live decision keeps 5,789,591 pairs = submission 2 exactly. On test the rule would drop 8,995 rows (0.50% of S1;
  France 4,633).
- Learned: the across-list signal as a hard rule is already spent by one-owner. As model features (M005) it can
  still help, but MATCH_TRAIN OOF one-owner sees only 180K S1, so M005 must also be judged with universe one-owner.
- Next: M005 with a universe-one-owner evaluation.

### 2026-09-26 · N05 · Pool-side competition (reverse retrieval) signal check · INFO
- Metrics: `pool_competition_check.json` · Script: `plan/checks/pool_competition_check.py` · Wall: ~6 min
- Hypothesis: FP rows are mostly records another S1 owns (N03: 63%); how a pool record is contested across all S1
  lists should separate them without labels.
- Result (165,545-S1 reference slice, full_single): 33.6% of rows contested (test 32.1%). Of TPs, 0.08% are rows
  where q is not the p_rerank-best S1 for the record. In the band, rows beaten by >=0.2 match 11.1% vs mean p_cal
  0.28; rows q wins by >=0.2 match 67.6% vs 0.61. Rule "drop kept row if another S1 has higher p_rerank" +0.00104
  [0.00094, 0.00115] vs live without universe one-owner (superseded by N05b).
- Learned: a real residual signal inside the band; the rule's gain was mostly the one-owner coverage gap.
- Next: N05b.

### 2026-09-26 · N04 · Decision rule on the test-like stratum (train labels) · INFO
- Metrics: `dense_stratum_rules.json` · Script: `plan/checks/dense_stratum_rules.py` · Wall: ~5 min
- Hypothesis: test lists carry more uncertain candidates, so a different threshold or expected-F might suit that regime.
- Result (full_single calibration slice, 165,545 train S1): S1 with >=1 row p_cal in [0.1,0.9) are 20.8% of S1,
  F0.5 0.95018 vs 0.98974 for the rest, and carry 56% of the loss. Best threshold on that stratum = live 0.69;
  expected-F vs threshold +0.00024 [-0.00065, +0.00107]. Lists >5: best 0.79, +0.00019.
- Learned: no decision-rule quick win. The loss is in ambiguous lists, and test has 1.25-2.7x more of them.
- Next: `plan/RCA_RESEARCH_PLAN.md` tier 1.

### 2026-09-26 · N03 · Train-vs-test shift diagnostic (test inputs only) · INFO
- Metrics: `test_shift_diag.json` · Script: `plan/checks/test_shift_diag.py` · Wall: 8 min
- Hypothesis: the leaderboard gap (internal 0.98161 vs public 0.966797) comes from France, from the denser test
  pool (5.75 vs 4.68 records per S1, all countries), or from stage-2 recall.
- Result: uncertain-band rows per S1 0.254 (train ref) vs test US 0.473, India 0.337, France 0.912. Stage-2 list size
  5.42 vs 5.60/5.63/8.99. Self-estimated F0.5 (Bernoulli(p_cal), candidates only) 0.9883 ref (actual 0.9887) vs
  test 0.9812/0.9851/0.9637. A list-statistics performance estimator gives test 0.9749/0.9775/0.9552, weighted
  0.9732. Adversarial AUC 0.986 is an IDF-scale artifact (max idf 16.150 vs 16.115); 0 live-model splits fall in
  the gap. Stage-2 tail truncation: not seen (last-slot-positive 8.9% test vs 11.4% ref; it does not predict
  misses on train). FP rows on ref: 37% orphans, 63% records owned by another S1.
- Learned: test is harder mainly through more near-duplicate distractors per list and France. The re-ranker was
  also truncated at 400/400 rounds on 45k queries (`rerank_train.json`). ~0.006 of the gap is not visible without labels.
- Next: `plan/RCA_RESEARCH_PLAN.md` (D1-D4, M1 cross-encoder feature, M2 density augmentation, R1 re-ranker retrain).

### 2026-09-26 · S2 · Submission 2 leaderboard · INFO
- Commit: 215b197 · Metrics: `match_train_full_single.json`, `match_predict_TEST.json` · log: `reports/test_usage_log.md`
- Public LB 0.966797 (S1: 0.966109). Internal 0.98161 held-out. Internal +0.0071 over S1, LB +0.0007.
- Learned: ~10% of the internal gain transferred; see N03.
### 2026-09-26 · CE-SMOKE1 · cross-encoder smoke (Friend B track, details in work/ce/) · INFO
- Metrics: work/ce/ce_rec_smoke_bf16/run.json (not artifacts/metrics/ — ce track lives in work/ce/).
- Hypothesis: LoRA r=16 on bge-reranker-v2-m3 attention + full head, bf16, batch 16×accum 4,
  trained on DEV_REST_180K pairs, learns pair match (eval AUC on held-out 1k S1 groups).
- Change vs first attempt: fp16 → bf16 (fp16 run went NaN by step 50, eval AUC 0.5215 — FAILED,
  log work/ce/ce_rec_smoke_train.log) + grad clip 1.0 + fail-fast NaN abort.
- Result: 1536 steps / 392 s; train loss 0.40 → 0.12; EVAL loss 0.1192, AUC 0.9906.
  Thermals (threads=4, workers=0): CPU 52–65°C, GPU 60–82°C steady, no guard pause.
- Learned: bf16 is required for this head on Ada; thermal headroom is ample for the full epoch.
- Next: full 1-epoch run on 976,897 DEV_REST_180K pairs (~4 h projected).

### 2026-09-26 · N02 · Experiment routine and this log · INFO
- Metrics: none (planning).
- `plan/EXPERIMENT_ROUTINE.md` written: stage-3 experiments on frozen MATCH_TRAIN candidates, ~40 min
  per run, paired Δ vs parent, error files per run. Loss analysis from `match_train.json`: FN inside
  candidates 47% of OOF loss (0.01219 of 0.02588), FP-involving 29%, blocking misses 24%.
- Learned: the precision/recall trade-off is already set by the decision threshold. Most of the loss the
  matcher can still fix is missed true pairs with p_matcher median 0.33, so features matter more than
  weighting the loss.
- Next: build `ber/exp.py`, reproduce M000 through it (must equal 0.97412).

### 2026-09-26 · N01 · Noise floor on MATCH_VALID · INFO
- Commit: fd77ee7 · Metrics: `validation_noise.json`
- Per-entity F0.5 std 0.1006; 82.4% of entities score exactly 1.0. Unpaired SE of the mean: 0.00071 at
  20K, 0.00022 at 200K, 0.00015 at 441K, 0.000078 at 1.655M.
- One-owner on vs off, paired: Δ +0.000007 [−0.000009, +0.000032], 2 entities changed, diff std 0.0016.
- Learned: unpaired comparisons on 20K cannot resolve gains below ~0.002; paired comparisons on fixed
  folds are required. One-owner is neutral at 0.9% coverage; its effect on test is unmeasured.
- Next: paired bootstrap in every M run.

### 2026-09-26 · S1 · Submission 1 · INFO
- Commit: fd77ee7 · Metrics: `match_predict_TEST.json` · Wall: 30 min predict (+141 min test candidates, `candidates_TEST.json`)
- 1,732,544 S1 rows, 5,688,259 pairs, validator passed. Mean predicted list size: France 3.28,
  India 3.24, US 3.33; empty share 5.6% / 6.2% / 5.9%.
- Learned: France prediction statistics look like US/India's, but that shows only that the output looks
  normal, not that it is correct (no labels).
- Next: record the leaderboard score here.

### 2026-09-25 · M000 · Stage-3 matcher baseline (LightGBM, 50 features) · ADOPTED
- Commit: c050879 · Metrics: `match_train.json`, `match_eval_MATCH_VALID.json` · Wall: 16.5 min train
- Hypothesis: pair features (name/address token-set, IDF, numbers) plus list-context features over the
  stage-2 candidates beat thresholding p_rerank alone.
- Change: 5-fold GroupKFold LightGBM binary, lr 0.05, 63 leaves, early stop 100; isotonic calibration;
  decision rule chosen on OOF.
- Result: OOF F0.5 0.97412 vs p_rerank-threshold floor 0.94655 (+0.02757). Rules on OOF: threshold
  0.97388, expected-F 0.97407, threshold+one-owner 0.97412, expected-F+one-owner 0.97433. Chosen
  threshold 0.70 + one-owner because expected-F did not clear `expected_f_min_gain` 0.001. MATCH_VALID
  0.97449 (−0.00037 vs OOF, within noise). Pairwise precision 0.9916, recall in candidates 0.968.
- Learned: `p_rerank` dominates gain (4.6M), then list features `l_p_ratio_max` (0.79M), `l_p_gap_max`
  (0.39M): a pair's score relative to the rest of its list carries the most signal. Worst segments:
  match_1 0.913, chain ≥10 0.964, India 0.970.
- Next: feature backlog F1–F9 in `plan/EXPERIMENT_ROUTINE.md` §8.

### 2026-09-25 · R2 · Stage 1+2 on validation S1 (one-shot) · INFO
- Commit: 1a2fb63 · Metrics: `rerank_eval_HOLDOUT_TEST.json` · Wall: 30.5 min
- F0.5 ceiling 0.99276, pair recall 0.9755, entity recall 0.99835, mean candidate size 5.43 (max 41).
- Learned: matches DEV_B (ceiling 0.99334, size 5.43) within 0.0006; stage 1+2 did not overfit DEV_A/DEV_B.
  This is the only validation-S1 score so far; the matcher has not been scored there.

### 2026-09-25 · R1 · Stage-2 re-ranker and leave-one-country-out · ADOPTED
- Commit: 2150e55 · Metrics: `rerank_eval_DEV_B.json`, `rerank_loco.json`
- Result: DEV_B candidate size cut from ~265 (E6) to 5.43 at F0.5 ceiling 0.99334 (−0.0022 vs E6).
  LOCO: trained on US, scored on India 0.98492 vs all-country 0.98897 (−0.0041); trained on India,
  scored on US 0.99654 vs 0.99626 (+0.0003).
- Learned: the US-only model loses 0.004 on India, so a country missing from training costs something
  in stage 2. France on test is in that position.

### 2026-09-25 · E6 · Stage-1 confirmation on DEV_B · ADOPTED
- Metrics: `s1_E6.json` — DEV_B ceiling 0.99550 vs DEV_A 0.99483; gate (DEV_B ≥ DEV_A − 0.003) passed.

### 2026-09-25 · E5 · Chain-size quota multiplier · DROPPED
- Metrics: `s1_E5.json`
- Hypothesis: queries whose name belongs to a chain (≥10 pool records) need a larger quota.
- Result: no setting passed the gate. min_chain10 × 2: chain≥10 ceiling +0.0047 (gate 0.005) at +10%
  size; × 3: +0.0070 but +21% size (gate 15%).
- Learned: chains gain from more candidates, but the cost is paid by every query. Chain ≥10 is still a
  weak segment in stage 3 (0.964, M000). Revisit only if stage 3 cannot close it.

### 2026-09-25 · E4 · Per-channel quotas · ADOPTED
- Metrics: `s1_E4.json`
- Result: best ceiling 0.99662 at mean size 741; chosen LEARN150/NAME0/ADDR50/PAIR100/XK50/CAT20 at
  0.99571, mean size 291 (within 0.001 of best at 39% of its size).

### 2026-09-25 · E3b · Learned stage-1 channel (logistic) · ADOPTED
- Metrics: `s1_E3b.json` — ceiling at K=300: learned 0.99223 vs hand-weighted 0.97793 (+0.0143).

### 2026-09-25 · E3 · Per-family posting caps · ADOPTED (smaller caps)
- Metrics: `s1_E3.json`
- Result: larger caps gained ≤ 0.0004 ceiling at up to 2× latency (NT 0.005: 0.99621 at 11.4 ms vs
  0.001: 0.99588 at 5.5 ms). Kept the small caps.

### 2026-09-25 · E2 · Blocking-key families · ADOPTED (5 kept, 2 dropped)
- Metrics: `s1_E2.json`
- Kept NP, SP, NC, AB, XK (ceiling gains 0.0055, 0.0042, 0.0029, 0.0059, 0.0052). Dropped SK (2
  exclusive pairs, gain 0) and PH phonetic (2 exclusive pairs, gain 0.00008).
- Learned: phonetic keys add nothing the n-gram and token keys don't already find.

### 2026-09-25 · E1 · Hand-weighted channel baseline · INFO
- Metrics: `s1_E1.json` — top-50 ceiling 0.96972, pair recall 0.9193; pair recall@150 0.9374 passed the 0.91 gate.

### 2026-09-25 · E0 · Mined abbreviation dictionary · ADOPTED
- Metrics: `e0_abbrev.json`
- Result: true-pair address Jaccard 0.6989 → 0.7577 (+0.0588); random negatives 0.0219 → 0.0232
  (+0.0013). Gate: true rise ≥ 0.005 and larger than negative rise.
