# Agent Prompt v2: Recall-first bucketing (blocking) for Business Entity Resolution

Authority: `AGENTS.md` (hard rules + Mac M-rules) > this file > `notes/problem_statement.md`.
Everything in `AGENTS.md` applies: fit-part only, no external data, allowlisted packages, every
number from a script that wrote `artifacts/metrics/*.json`, one heavy job at a time under `nice`,
update `PROGRESS.md` after every step, `git commit` after every phase.

Scope: candidate generation only (stage-1 retrieval + stage-2 candidate re-ranker). The heavy
matcher (LightGBM on rich features, threshold, decision rules) is OUT of scope.

## 0. What is already known (do not re-derive; read the files)
Read `reports/bucketing_diagnostics.md` and these JSONs first: `diag_scripts.json`,
`diag_blocking.json`, `diag_breakdown.json`, `diag_rerank.json`, `diag_blocking2.json`,
`diag_quota.json`, plus the older `blocking*.json`. Key facts:
- Goal: over-retrieval is fine; a true match that never enters the candidate set is lost for good.
  But compute is finite: the heavy matcher's per-pair Python featurizer runs about 8.3K pairs/s
  on this Mac (`logs/feat_train.log`: 9.0M rows in about 18 min).
- Test = 1,732,544 S1 entities. Every +1 avg candidate = +1.73M matcher pairs.
- `candidate_pairs.tsv` must be the LAST set the final matcher scores; the organizers analyse it
  for recall ceiling and reduction ratio. At about 13 bytes per ID, avg 150 candidates ≈ 3.4 GB of
  TSV, avg 60 ≈ 1.35 GB.
- **Bug:** `normalize.py` v1 erases every non-Latin letter. That erases 699K train-pool names
  (17% of Indian pool records) and 807K test-pool names.
- Loss is mostly ranking, not reachability: 98.72% of true pairs are reachable in the full union,
  but only 92.5% make the top 150 of the best single formula.
- Name channels go silent for common-word names: the df caps (token >20K, trigram >8K) drop
  every key, and chain names with one typo lose the exact key.
- A single additive score cannot fuse channels (adding PAIR/ROM to the sum hurts small-K
  ranking). A per-channel quota union matches single-score recall with 2.6× to 4× fewer candidates.
- Postal-only keys: 0 exclusive hits (postal tokens are already in the address channel).
  BK-tree / automaton: rejected (see `blocking_report.md`). Do not revisit either without a new
  hypothesis and a number.

## Evaluation protocol (use for every experiment)
- Query set A = the existing 10K fit queries (`random.Random(123).sample(fit_ids, 10000)`); use
  it for tuning. Query set B = a DISJOINT 10K fit-part sample (seed 456, excluding A); use it
  to confirm the final config once, so quotas are not overfit to A.
- Report per config: pair recall, entity recall (non-singletons with ≥1 true match), mean and
  p99 candidates per query, ms/query, peak RSS. Report recall by segment too: chain size (1,
  2–9, ≥10), country, pool-name class (ascii / latin_ext / mixed / nonlatin), empty pool
  address. Pool-name class and chain size come from `diag_scripts.classify` and S1 normalized-name counts.
- LOCO (France proxy): for the final config, tune on India-only queries and evaluate on US-only
  queries, and the reverse. Report the recall drop.
- Val (441K) is used ONCE at the very end, for reporting only. Never scored on test.

---

## Phase 1: Normalization v2 (budget 1 h)
1. Change `_PUNCT_RE` so non-Latin LETTERS survive: strip punctuation, keep `\w` letters of any
   script. Map `œ→oe, æ→ae, ß→ss, º→o, ø→o, ł→l, đ→d` (all Latin letters NFKD does not decompose).
   Bump `NORMALIZE_VERSION = 2`.
2. Add `name_key(raw)`: if the name has Indic letters, return `normalize_name(romanize_words_schwa(raw))`
   (`src/translit.py`, stdlib `unicodedata` only), else `normalize_name(raw)`. Keep both the
   native normalized form and the romanized form.
3. Improve `translit.py` using TRAIN evidence only: collect fit-part true pairs (Indic pool name ↔
   Latin S1 name). Measure token-level agreement (romanized token vs S1 token: exact / metaphone /
   Levenshtein ≤1). Fix the top systematic mismatches: nasal/anusvara handling, vowel-length
   collapse, v/w, ph/f, final schwa, z/j (nukta). Also add a learned token dictionary for frequent
   tokens (e.g. romanized 'limitet' → 'limited'), built from fit-part aligned pairs by
   co-occurrence counts (min support 20). Report the before/after token agreement rate.
   Log in `reports/assumptions.md` that the dictionary is train-derived.
4. Unit tests (`src/test_normalize.py`): France accents, Œ, Devanagari, Tamil, mixed Latin +
   Devanagari address, empty string.

Output: `reports/normalize_v2.md` + `artifacts/metrics/normalize_v2.json`.

## Phase 2: Channel set (budget 2 h)
Rebuild the pool indexes with normalize v2 (reuse `build_pool_index.py`, `build_addr_index.py`,
`build_aux_index.py`; write to `artifacts/index_v2/`, keep v1 for comparison). Channels:

| id | key | notes |
|---|---|---|
| EX | exact normalized name AND exact suffix-stripped name | strip via `SUFFIX_TOKENS` (train-derived) |
| NT | rare name token (df ≤ cap) | on `name_key` text |
| TR | name char-trigram (df ≤ cap) | on `name_key` text |
| PH | metaphone per token | cheap, keep |
| AD | address token (df ≤ cap) | includes postal tokens |
| PAIR | unordered name-token pair (first 8 tokens) | rescues common-word and typo'd chain names |
| ROM | romanized-name tokens/trigrams | same token space as NT/TR once Phase 1 lands |
| CAT | space-free suffix-stripped name, plus pool tokens ≥6 chars (domain names) | 198/444 unreachable hits; test exclusivity |
| APAIR | (name token × address token) pairs, both over the single-key df cap | experiment: rescues chains where both name and city are common |

For each channel report: exclusive pairs (reached ONLY by that channel), reachability gain,
posting count, index size on disk, and query time. Drop a channel only if exclusive gain
< 0.05% of pairs AND it costs >10% of query time. Sweep the df caps (NT 5K/20K/50K,
TR 4K/8K/16K, AD 5K/20K/50K): a higher cap raises reach but also union size and time.

Output: `reports/channels_v2.md` + `artifacts/metrics/channels_v2.json`.

## Phase 3: Stage-1 = per-channel quota union (budget 1.5 h)
Candidates = ∪ over channels of that channel's top-q by its own score, plus the top-q of the
combined sum.
1. Grid over quotas (start from `diag_quota.py`; add CAT/APAIR if kept). Plot the Pareto curve
   of pair recall vs mean size. Pick the cheapest config reaching pair recall ≥ 0.965 on set A,
   then confirm on set B.
2. Chain-adaptive quota: when the exact-name bucket (or the best PAIR bucket) is larger than N,
   raise the ADDR and PAIR quotas for that query. Choose N and the multiplier from the rank data
   (segment chain ≥10 was 0.7958 @150); report recall and cost for chain queries and overall.
3. Country: soft only. Measure what a country-mismatch demotion (not removal) does to size and
   recall. Never hard-filter (France is unseen; `AGENTS.md` rule 4).
4. Save stage-1 candidates WITH their per-channel scores and ranks (parquet, chunked), so stage 2
   never recomputes them: fit sample, set A, set B, val.

Output: `reports/stage1_quota.md` + `artifacts/metrics/stage1_quota.json`.

## Phase 4: Stage-2 = learned candidate re-ranker (budget 2 h; training a small model IS allowed here)
Purpose: shrink ~500–900 stage-1 candidates to an adaptive ~20–100 while keeping ≥99% of the
stage-1 recall. This model's output is `candidate_pairs.tsv`.
1. Cheap features only (target < 3 ms per query for 800 candidates, vectorized):
   - stage-1 channel scores and per-channel ranks; query-coverage ratios;
   - rapidfuzz `cdist` (C-level, `workers`) token_set_ratio and ratio on name_key, and
     token_set_ratio on normalized addresses;
   - postal-token equality in 3 states; candidate exact-name bucket size (chain signal);
   - country agree / unknown; source S2/S3.
   Pre-compute normalized and romanized pool strings ONCE into a memory-mapped array (the
   per-query Python decode + normalize cost ~28 ms/query in `diag_rerank.py`).
2. Model: LightGBM binary or lambdarank, trained on fit-part queries disjoint from sets A and B
   (the 60K fit sample is fine), GroupKFold by S1 entity. `n_jobs` ≤ cores − 2.
3. Cut rule: keep a candidate if the calibrated p ≥ p_min, with K_min = 10 and K_max = 150.
   Choose p_min on OOF so that pair recall ≥ 0.99 × stage-1 recall. Report the recall vs mean
   size curve.
4. Report on set B: final candidate pair recall, entity recall, mean/p99 size, segment table,
   and the projected test pairs (1.73M × mean size) and TSV size.

Output: `reports/stage2_reranker.md` + `artifacts/metrics/stage2_reranker.json`.

## Phase 5: Cost model and final recommendation (budget 45 min)
Write `bucketing_strategy_final.md`:
1. Final config: channels, caps, quotas, adaptive rules, re-ranker features, p_min, K_min/K_max.
2. Old vs new: current production (top-150: 0.922 pair / 0.987 entity) vs new stage-1 and
   stage-2 numbers on set B and LOCO.
3. Measured throughput per stage (queries/s per worker) → projected wall-clock for the test
   run on this Mac (8 cores, 16 GB).
4. Remaining gap: what is still unreachable, by category, with 5 real example pairs.
5. What changes for the matcher: normalize v2 features, and name features on romanized text
   (the current matcher computes name similarity on "" for 17% of Indian pool records).

## Rules
- No external data, APIs, transliteration libraries, gazetteers, or pretrained transliteration
  models. `unicodedata` is stdlib; any mapping beyond it must be derived from train data and
  logged.
- Nothing is tuned on val or test. Test files are touched only to build the test-pool index at
  inference (unsupervised df/idf, logged in `reports/test_inspection_log.md`).
- Memory: never hold all stage-1 candidates for the full test set in RAM. Stream by chunk to
  parquet.
- Every report cites its JSON. Negative results are results.
