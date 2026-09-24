# Test inspection log (C7: structural only, no matching/scoring/tuning)

## 2026-09-25 Phase 0.1
- WHAT: row counts, schema/columns, ID prefix + S1 uniqueness, distinct country labels+counts, non-ASCII/non-Latin rates per country, top-30 name/address tokens per country, on student_resource/dataset/test/test_source{1,2,3}.tsv via src/phase0_summary.py.
- WHY: confirm France present structurally; check normalization will not break on French text.
- FORBIDDEN (not done): no matching/scoring against test, no threshold/feature tuning on test, no rules from specific test rows, no hand-labeling.
- ARTIFACT: artifacts/metrics/test_inspection.json
