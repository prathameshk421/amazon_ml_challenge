# EDA report (all numbers from artifacts/metrics/eda_*.json, data_summary.json, country_agree.json)

Sample basis: fit part (1765458 S1 entities) for conclusions; signal study on 12000 sampled
fit entities (6000 US + 6000 India, seed 42) with 44027 positives, 880540 random negatives
(20/positive), 168366 hard negatives (<=20/entity) mined from a 411056-record pool sample.
TF-IDF fit on the mine-pool only (unsupervised). Val untouched.

## Structural

- Scale: train S1 2206821 (fit 1765458), S2 5034616, S3 5285603; pool 10320219.
  Conclusion: no full S1xpool matrix is ever feasible; blocking is mandatory.
- Countries (train): S1 US 1323633 / India 883188; pool same two labels, identical format in
  all sources (no hand-mapping needed, but still treated as open set).
- Empties: S1 has zero empty fields; S2 has 168967 empty addresses (US 111121, India 57846),
  S3 has 175916 (US 110968, India 64948), i.e. ~3.3% of pool records lack addresses.
  Conclusion: address features need a missing state; name must carry those pairs.
- Lengths (median bin): names <30 chars all sources; addresses S1 <60, S2 <40, S3 <60.
  Conclusion: short strings, so edit/Jaccard/TF-IDF features are cheap and appropriate.
- Duplicates within source (exact lowercased name, fit-S1 / full pool): S1 has 54421 India +
  84087 US dup-name groups covering 640960 rows; S2/S3 each have ~286K groups covering
  ~1.0M rows. Top: 'primary care group' (253 S1 entities), 'primary care' (397 S2 rows).
  Conclusion: identical names recur heavily across entities, so name-only matching is
  insufficient and address is the tiebreaker (motivates chain-aware error buckets).
- Character sets: S1 is nearly all ASCII (554 non-ASCII rows, all India); S2/S3 carry
  904496 + 774056 non-ASCII India rows and 202224 + 215616 US rows (transliterations,
  e.g. Devanagari names). Conclusion: NFKD/accent-strip normalization is required, and
  the clean-ASCII S1 vs noisy pool asymmetry means normalization gains concentrate
  on the pool side.
- Name suffix frequencies (fit-S1 + pool): India limited 1624613 / private 1520701 /
  ltd 769711 / pvt 509378 / llp 171312; US llc 1392833 / inc 1016567 / corp 266272 /
  co 205267 / lp 107384 / pllc 66618; honorifics sri 55080 / shri 54930 / shree 32365.
  Conclusion: legal-suffix variation is the dominant name noise; dictionary in
  src/normalize.py v1 maps corp/inc/ltd/pvt/co/svc/assoc/bros/shri/shree (+ampersand).
- Address abbreviation frequencies: US rd 603394 vs road 718496, st 649210 vs street 784912,
  dr 547452, ave 450290, ln 232222, ct 197445, blvd 52038, apt 42384, ste 6942, hwy 25150,
  pkwy 15397; India near 247541, opp 130638, behind 35909, no 2547212, plot 417504.
  Conclusion: S1 uses full street forms while S2/S3 abbreviate, so expansion (v1 dict)
  directly closes the S1-pool gap; landmark tokens (near/opp/behind) are India-specific
  content worth keeping, not stripping.

## Signals ranked

Ranked by ROC-AUC on hard negatives (then histogram overlap); chart reports/signal_auc.png.

| signal | auc_hard | overlap_hard | auc_rand | mean pos/hard/rand |
|---|---|---|---|---|
| a_jacc | 0.9719 | 0.065 | 0.9754 | 0.669 / 0.023 / 0.012 |
| a_snd | 0.9682 | 0.088 | 0.9728 | 0.704 / 0.036 / 0.021 |
| a_tfidf | 0.9637 | 0.068 | 0.9670 | 0.813 / 0.029 / 0.013 |
| a_meta | 0.9574 | 0.089 | 0.9594 | 0.711 / 0.095 / 0.084 |
| a_lev_norm | 0.9370 | 0.139 | 0.9438 | 0.770 / 0.343 / 0.317 |
| a_editex | 0.9257 | 0.158 | 0.9333 | 0.773 / 0.393 / 0.369 |
| a_digit | 0.9063 | 0.194 | 0.9079 | 0.723 / 0.011 / 0.008 |
| a_lev_raw | 0.8927 | 0.284 | 0.9063 | 0.561 / 0.266 / 0.250 |
| n_tfidf | 0.7497 | 0.415 | 0.9271 | 0.780 / 0.629 / 0.019 |
| n_snd | 0.7109 | 0.404 | 0.9220 | 0.672 / 0.490 / 0.026 |
| n_meta | 0.7061 | 0.390 | 0.9101 | 0.657 / 0.482 / 0.025 |
| n_jacc | 0.7009 | 0.402 | 0.9099 | 0.647 / 0.477 / 0.024 |
| a_postal | 0.6636 | 0.673 | 0.7207 | 0.891 / 0.564 / 0.449 |
| n_lev_norm | 0.6566 | 0.598 | 0.8953 | 0.769 / 0.724 / 0.325 |
| n_lev_raw | 0.6527 | 0.588 | 0.8410 | 0.686 / 0.602 / 0.263 |
| n_editex | 0.6474 | 0.610 | 0.8908 | 0.773 / 0.740 / 0.385 |
| country | 0.5222 | 0.956 | 0.7498 | 1.000 / 0.956 / 0.500 |

- Address similarities dominate hard-negative separation (AUC 0.89-0.97, overlap <=0.28)
  because hard negatives were mined to be name-similar; the address is the tiebreaker.
- Best name signal is TF-IDF char-ngram cosine (hard AUC 0.7497), then phonetic set-Jaccard
  (soundex 0.7109, metaphone 0.7061), then token Jaccard (0.7009), then Levenshtein (0.6566).
- Normalization gain (raw -> normalized Levenshtein): +0.054 AUC on random negatives
  (0.8410 -> 0.8953), negligible on hard negatives (0.6527 -> 0.6566) since hard negatives
  are name-similar by construction; normalization still helps recall-side blocking.
- Phonetic is country-asymmetric: metaphone hard-AUC is 0.8065 on US but 0.6146 on India
  (soundex 0.8155 vs 0.6168); Editex is useless on India (0.5220, hard mean exceeds pos
  mean 0.779 vs 0.690). Conclusion: keep soundex/metaphone as features, expect the model
  to weight them modestly; Editex is a drop candidate in ablation.
- Transposition check: 6.05% of positives (2665/44027) share identical name token multisets
  with different order (mean Jaccard 1.0 vs mean lev 0.723), so token-order-free signals
  (Jaccard, TF-IDF, token_set) are required alongside edit distance.
- Country agreement: 100% of 44027 sample positives agree (differ 0.0), confirmed on
  692697 pairs over 200261 GT rows (agree 1.0, missing 0). Decision: strong SOFT feature
  with unknown state, never a hard filter (France is unseen; cross-country truth cannot
  be ruled out on test). See reports/assumptions.md.
- a_postal (shared-or-both-missing indicator) is weak (hard AUC 0.6636, overlap 0.673);
  Phase 3 must use an explicit 3-state postal feature instead.

## Ground-truth structure

- Fit singleton rate 0.0558 (98598/1765458); match counts peak at 3 (424561 entities),
  tail to 11 (33 entities); only 5.4% of non-singletons have exactly 1 match.
- Of fit non-singletons, 85.2% match in BOTH S2 and S3, 6.9% S2-only, 7.9% S3-only.
  Conclusion: S2 and S3 overlap heavily; scoring must consider both pools jointly.
- Owner check: each pool record has <=1 owner (7638365 raw == 7638365 unique GT links,
  0 missing from pool). This enables record-level consolidation (rule R4).
- Orphans: 1340997 S2 records (26.6%) and 1340857 S3 records (25.4%) appear in NO truth
  row. Conclusion: the pool is ~1/4 distractor records; precision matters (fits F0.5).
- Chains: 180422 normalized S1 names occur in >=2 S1 entities, covering 881492 entities
  (40% of S1); 103611 pairs, 32546 triples, 11036 with >=10 (e.g. 'primary care group'
  x253, 'ear nose and throat group' x251). Conclusion: same-name-different-entity is the
  central difficulty; address decides, and per-record winner-takes-all (R4) is motivated.
- Multi-branch example (S1 Kurnool Wires, 11 true matches): same address with typos
  ('Wrrier', 'Wiades', 'Kurnoo1'), suffix churn ('Corp', 'Corporation', ''), 't/a' trade
  prefix ('Vantagevio t/a Kurnool Wires'), component reorder ('Andhra Pradesh' first),
  'AP' abbreviation. Conclusion: one entity's matches span nearly every noise pattern,
  so the matcher needs all signal families, not one silver bullet.
- Same-name-wrong-place example: 'Happy Nails, LLC' (Middletown OH) vs 'HAPPY NAILS LLC'
  in Santa Maria CA and Haltom City TX (both non-matches): name similarity 1.0 with
  address similarity ~0. Conclusion: name-only blocking will propose these; the matcher
  must learn name-high/address-low => reject.

## Noise pattern catalog

Each entry: pattern, frequency in the 44K-positive sample, real example rows.

1. legal-suffix gap: 6881 positives (15.6%) equal only after suffix-strip. S1 'HU Desert
   Alto LLC' vs 'HU DESERT ALTO' (1945 214TH LN, BUCKEYE, AZ).
2. ampersand-vs-and/punctuation: 583 positives. 'Oconnor & Sharma Clinic' vs 'Oconnor
   Sharma Clinic Partners' (same address); 'Vang & Satterwhite LLC' vs 'Vang + Satterte LLC'.
3. word-order transposition/duplication: 3002 positives with Jaccard 1.0 but lev < 0.9.
   'Graham, Mccollum and Sullivan PC' vs 'Graham, Mccollum And Sullivan Sullivan Pc'.
4. typos/truncation: 14223 positives with name lev in [0.8, 1.0). 'HU Desert Alto' vs
   'HU DESERT ALT LLC'; address reorder 'AZ, BUCKEYE, 1945 214TH LANE'.
5. transliteration/phonetic: 1153 positives with name lev < 0.6 but metaphone >= 0.5.
   'Quon Inc' vs 'QUON' (271C PLEASANT ST); 'RPM Coinshares LLC' vs 'RPM LLC Center'
   (PO BOX 7147 variant address).
6. landmark addresses: 2552 positives contain near/opp/behind. 'Legacy Equity Company'
   vs 'Legacy Equity Company' ('Unit SUITE B' vs 'Unit Suite B', 'Missouri' vs 'MO');
   'HAZELWOOD, #1 VILLAGE SQUARE ... N/A, MO'.
7. empty pool address: 1839 positives (4.2%) have empty S2/S3 address, e.g. 'Guillema
   Miller Advanced Exchange Inc' with ''. Conclusion: name-only features must cover these.
8. domain names: 1757 positives. 'Phaedra Zeng Pegasus Corp' vs 'phaedrazengpegasus.com';
   'Continental Foundation LLC' vs 'foundationcontinental.com' (word-order flip inside domain).
9. same-name hard negatives (chain confusion): 3839 hard negatives (2.3%) share the exact
   normalized name with a different entity (Happy Nails examples above).
10. acronym-like: 5.4% of sampled hard negatives have equal token initials (bucket (2)
    exists but is small; embedding test in Phase 5 should check it explicitly).
