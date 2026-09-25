# Blocking report (numbers from artifacts/metrics/blocking.json, blocking2.json, blocking_phon.json)

Pool: 10320219 records (S2 5034616 + S3 5285603). Eval: 10000 fit queries (seed 123,
same set throughout), truth mapped to pool row-ids. Reduction = 1 - avg_cands/pool.

## Method comparison (full pool)

| method | pair recall | entity recall | avg cands | reduction | note |
|---|---|---|---|---|---|
| exact normalized name | 0.2825 | 0.6538 | 13.0 | 0.999999 | dict lookup |
| token union (df<=20000) | 0.7313 | 0.8504 | 6366.0 | 0.999383 | too many |
| trigram overlap top-10/25/50 | 0.0998/0.1300/0.1508 | 0.1513/0.1823/0.2073 | 4.6/11.4/22.8 | ~1.0 | weak alone |
| trigram idf top-10/25/50 | 0.1007/0.1308/0.1517 | 0.1515/0.1823/0.2073 | 4.6/11.4/22.8 | ~1.0 | same |
| metaphone top-20 | 0.3829 | 0.5690 | 19.4 | 0.999998 | cheap |
| union (exact+token+tri50) | 0.7700 | 0.9272 | 6383.1 | 0.999381 | count problem |
| union all (+idf+phon) | 0.7766 | 0.9316 | 6392.7 | 0.999381 | count problem |

- Single top-N methods have low ceilings on a 10.3M pool: trigram top-50 finds only 15%
  of true pairs (top-50 is crowded out by common trigrams); exact-name finds 28% of pairs
  but 65% of entities (chains share names).
- Token-union carries recall (0.73) at an impossible count (6366/query => 2.8B pairs on val).
- Phonetic top-20 is the best cheap source (0.38/0.57 at 19 cands).

## Ranked union (idf-weighted score, top-K)

Score = exact(+100) + name-token idf + trigram idf (df<=8000) + addr-token idf +
0.2 x shared-metaphone; keep top-K. 1.7 ms/query.

| K | pair recall | entity recall | reduction |
|---|---|---|---|
| 50 | 0.8812 | 0.9729 | 0.999995 |
| 100 | 0.9099 | 0.9841 | 0.999990 |
| 150 | 0.9218 | 0.9873 | 0.999985 |
| 250 | 0.9351 | 0.9912 | 0.999976 |
| 500 | 0.9471 | 0.9936 | 0.999952 |

- Source attribution of found pairs (top-500): address-token 0.95, name-token 0.76,
  phonetic 0.68, trigram 0.44, exact 0.30. Address-token blocking is the hero: 95% of
  recovered true pairs share an address token (city/state/PIN words survive name noise).
- K=150 chosen: pair ceiling 0.922, entity ceiling 0.987 at 150 cands/query
  (66M pairs on val — featurizable tonight). K=250 adds +0.013 pair recall for +67%
  compute; logged as tomorrow's option.

## BK-tree (own implementation, 200K pool sample x 2000 queries)

| k | pair recall | entity recall | avg cands | ms/query |
|---|---|---|---|---|
| 1 | 0.3264 | 0.3406 | 0.34 | 0.3 |
| 2 | 0.3472 | 0.3623 | 0.90 | 2.6 |
| 3 | 0.3819 | 0.3986 | 10.35 | 8.4 |
| 4 | 0.4722 | 0.4928 | 38.46 | 16.1 |

- Recall measured only over truth records present in the 200K sample. k=4 roughly doubles
  k=1 recall at 50x query cost. Full-pool BK-tree rejected: per-query cost grows with pool
  size (node visits), while postings indexes have sublinear per-query cost; at 10.3M pool
  a Python BK-tree cannot serve 500K queries tonight. Trigram+token indexes cover the same
  edit-recall function approximately (TR attribution 0.44).

## Phonetic marginal

- Standalone metaphone top-20: 0.3829/0.5690 (19 cands).
- Exclusive retrieval marginal (pairs found ONLY via phonetic, no exact/token/trigram/addr
  vote): 0 of 34745 true pairs (blocking_phon.json). Address-token exclusivity is 5859
  pairs (16.9%) by contrast; exact/name-token/trigram exclusives are 64/15/4.
- Ranking ablation (PHON_W 0.2 -> 0.0, same 10K queries): top-150 pair recall 0.92177 ->
  0.92180 (delta +0.00003), top-500 0.94713 -> 0.94684. Negligible either way.
- Verdict: phonetic adds nothing to blocking retrieval or ranking at top-150 (kept in the
  scoring formula where it is harmless; candidates on disk match the formula exactly).
  Phonetic's value, if any, is as a MATCHER feature (Phase 1: name-soundex hard-AUC 0.71,
  US-only 0.82), tested by ablation in Phase 3.

## Unrecovered (10 real true matches missed by top-500 union)

Dominant pattern: native-script pool names (Devanagari/Gujarati/Tamil) with zero shared
Latin tokens, e.g. 'Green Ram Marketing Pvt Ltd' vs 'ग्रीन राम मार्केटिंग प्रा. लि.';
'Indo Exports Limited' vs 'இண்டோ எக்ஸ்போர்ட்ஸ் லிமிடெட்'. Also: '(Ltd) Best Tech' vs
'Best Tech Limited' (affix-order), 'cityrichm0ndliteracy.com' (leet domain).
Conclusion: the ~5% pair-recall gap is mostly transliteration; closing it needs
transliteration-aware blocking (tomorrow: mined romanization pairs or embedding index).

## Recommendation (ONE configuration)

Ranked idf-union top-150 (exact + name-token df<=20K + trigram df<=8000 + addr-token +
metaphone df<=20000). Ceiling: pair 0.922 / entity 0.987 at 150 cands, 1.7 ms/query.
Candidates saved: artifacts/candidates/fit_sample_K150.parquet (60K fit-sample entities),
artifacts/candidates/val_K150.parquet (full 441363 val). LOCO reuses val slices by country.
Levenshtein automaton: skipped (45-min optional; trigram+token cover it; logged).
