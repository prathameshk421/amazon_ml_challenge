# Overnight run log

## 2026-09-25 01:43-01:52 Phase 0 DONE (elapsed ~9min)
- Safety self-test: rm of own probe file succeeded (allowed by AGENTS M2); discrepancy vs prompt logged in reports/assumptions.md, continued.
- Machine: ncpu=8, mem=17.2GB, disk free=1.9TB, AC power 64% charging.
- Artifacts: src/metric.py + src/test_metric.py (all pass), artifacts/split.json (val=441363/fit=1765458, seed 42 stratified), artifacts/metrics/{data_summary,split,gt_checks,test_inspection,licenses}.json, reports/{data_summary,test_inspection_log,licenses}.md.
- Key facts: S1==GT ID sets; all 7638365 GT links in pool, 0 missing; each pool record <=1 owner (enables R4); train countries {US,India} same format all sources; test adds France ~15%; singleton rate 0.0558; max 11 matches; S2/S3 have 169K/176K empty addresses; S1 nearly all ASCII while S2/S3 heavily non-ASCII (S1 is clean reference).
- Errors: none. Tmp id files removed.
