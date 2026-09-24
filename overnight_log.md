# Overnight run log

## 2026-09-25 02:34 Phase 1 DONE (elapsed ~50min)
- 1a: artifacts/metrics/eda_struct.json (lengths, empties x country, dup names, top tokens)
  + normdict_evidence.json; src/normalize.py v1 (NORMALIZE_VERSION=1).
- 1b: artifacts/metrics/eda_signals.json (17 signals x AUC+overlap on random+hard) +
  eda_catalog.json + artifacts/eda_pairs_sample.parquet (1092952 rows). Key: address signals
  dominate hard AUC (0.89-0.97); best name = TF-IDF (0.75); phonetic US-only (0.81 vs 0.61);
  country agree 1.0 (soft feature only); 6% transposition-like positives.
- 1c: artifacts/metrics/eda_structure.json + country_agree.json. 85% entities match both S2+S3;
  orphans 26%; 180K chains cover 40% of S1; each record <=1 owner (R4 enabled).
- Wrote reports/eda_report.md + reports/signal_auc.png.
- Errors: eda_signals hard-mining stalled on high-df trigrams (killed pid 86275, retry 1);
  fixed with df cap + most_common(300)/k>=2, completed in 4.8min (pid 93308). eda_catalog
  print-crash on float entry (retry 1, JSON had been written).

## 2026-09-25 01:43-01:52 Phase 0 DONE (elapsed ~9min)
- Safety self-test: rm of own probe file succeeded (allowed by AGENTS M2); discrepancy vs prompt logged in reports/assumptions.md, continued.
- Machine: ncpu=8, mem=17.2GB, disk free=1.9TB, AC power 64% charging.
- Artifacts: src/metric.py + src/test_metric.py (all pass), artifacts/split.json (val=441363/fit=1765458, seed 42 stratified), artifacts/metrics/{data_summary,split,gt_checks,test_inspection,licenses}.json, reports/{data_summary,test_inspection_log,licenses}.md.
- Key facts: S1==GT ID sets; all 7638365 GT links in pool, 0 missing; each pool record <=1 owner (enables R4); train countries {US,India} same format all sources; test adds France ~15%; singleton rate 0.0558; max 11 matches; S2/S3 have 169K/176K empty addresses; S1 nearly all ASCII while S2/S3 heavily non-ASCII (S1 is clean reference).
- Errors: none. Tmp id files removed.
