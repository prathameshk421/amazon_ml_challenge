# Bucketing (blocking) diagnostics, 2026-09-25 (interactive session, no model training)

All queries: the same 10,000 fit-part S1 entities (seed 123) as `blocking2.json`, 34,745 true pairs.
Val and test ground truth untouched. Every number below is in the cited `artifacts/metrics/*.json`.

## 1. Writing systems (`diag_scripts.json`)
- 699,389 train-pool names are entirely in Indic scripts (S2 455,759 + S3 243,630; Devanagari
  most common, then Telugu, Kannada, Tamil, Bengali, Gujarati). `normalize_name()` turns all of
  them into "" because `_PUNCT_RE = [^0-9a-z\s]` deletes non-Latin letters. Test pool: 806,829.
  Their addresses are mostly Latin, often with a native-script state name appended ("mixed").
- S1 (train and test) is 100% Latin. France (test only) is Latin with accents: 40,789 S1 names and
  73,335 S1 addresses carry accents, which NFKD already handles. Only 'Œ' is lost (≤75 rows per
  file) and 'º' appears in about 11.8K pool addresses per source.

## 2. Where true matches sit in the full union (`diag_blocking.json`, `diag_breakdown.json`)
- Full union: mean 25,598 candidates/query (p99 66,836), 2.3 ms/query. 98.72% of true pairs are
  reachable; the loss is mostly **ranking**, not reachability.
- Pair recall@150: current formula (exact +100) 0.9171; exact +10 0.9252. At K=25: 0.8182 vs 0.8913.
- By segment, current formula @150: chain ≥10: 0.7958; non-Latin name: 0.7222; empty pool
  address: 0.6342; non-chain: 0.9525.
- Of 2,155 pairs reachable but ranked >150 (exact +10), 1,272 get **no vote from any name
  channel**. Two causes:
  (a) the name was erased (Indic script);
  (b) every name token has df >20,000 and every trigram df >8,000, so a name made of common
  words is invisible unless it matches exactly. For chains ≥10, the exact key voted for 1 of 401
  deep pairs and a name token for 117; address voted for 284.
- 444 pairs are unreachable (176 Indic names, 150 empty addresses). Candidate new keys would reach
  414 of them: romanized token 374, romanized metaphone 391, space-free concatenation 198,
  postal 0. Postal is already inside the address-token channel.

## 3. Re-rank a top-2000 shortlist with hand formulas (`diag_rerank.json`, 2,000 queries)
- Ceiling inside the top-2000: 0.9649. Romanized-name token_set + address token_set + 0.1×stage-1
  rank: @10 0.9076 vs 0.8722 stage-1 order, @150 0.9343 vs 0.9332.
- Without romanization the same re-rank loses (@150 0.8719): name similarity is 0 for erased names.
- Verdict: hand formulas help only at very small K; a learned re-ranker is the next step.

## 4. New key families (`diag_blocking2.json`, aux index `artifacts/index/aux.npz`)
- PAIR keys (unordered token pairs) and ROM keys (romanized Indic names, tokens + trigrams, df
  rescaled to full-pool frequency). Reachability 0.9872 → 0.9935. Union 25.6K → 31.9K, 3.8 ms/query.
- Adding their scores into one additive sum HURTS small-K ranking (F8 @150 0.9062 vs F1 0.9252)
  but helps depth (@2000 0.9694 vs 0.9577). So channels must not be fused by a naive sum.

## 5. Per-channel quota union (`diag_quota.json`)
| config | pair recall | entity recall | mean size | p99 size |
|---|---|---|---|---|
| single sum top-150 | 0.9310 | 0.9913 | 150 | 150 |
| single sum top-500 | 0.9469 | 0.9936 | 499 | 500 |
| single sum top-2000 | 0.9622 | 0.9955 | 1980 | 2000 |
| 50 per channel ×5 | 0.9466 | 0.9924 | 192 | 242 |
| B300+N100+A100+P100+R50 | 0.9623 | 0.9950 | 497 | 630 |
| B500+N200+A200+P200+R100 | 0.9681 | 0.9958 | 888 | 1155 |
| 500 per channel ×5 | 0.9717 | 0.9964 | 1755 | 2382 |

Row names: B = combined name+address score, N = name, A = address, P = token pair, R = romanized
name; each number is that channel's top-q. The quota union reaches the same recall with 2.6× to
4× fewer candidates than a single score.

## Recommended direction (details in `archive/agent_runs/bucket_prompt_v2.md`)
1. Normalization v2: keep Indic letters and add a romanized form.
2. Add PAIR and ROM channels.
3. Stage-1 = per-channel quota union (~500 to 900 candidates, pair recall ~0.962 to 0.968).
4. Stage-2 = learned candidate re-ranker with an adaptive cut to ~50 to 100 per entity; its
   output is `candidate_pairs.tsv`.
5. Heavy matcher on those candidates only.
