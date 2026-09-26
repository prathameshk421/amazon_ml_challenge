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
| submission | test | leaderboard | not recorded | S1 | `match_predict_TEST.json` |

## Open questions

- Submission 1 leaderboard score vs OOF 0.97412 → the OOF-to-test offset. Not logged yet.
- Paired SE of a feature change at 180K. Unmeasured until the first M run (N01 only covers one-owner).
- How much the OOF score is inflated by `translit_dict` being mined from DICT_SRC labels (VALIDATION_PLAN P4). Unmeasured.

---

## Log

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
