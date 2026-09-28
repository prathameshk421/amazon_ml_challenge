# Test inspection log (C7: structural only, no matching/scoring/tuning)

## 2026-09-25 Phase 0.1
- WHAT: row counts, schema/columns, ID prefix + S1 uniqueness, distinct country labels+counts, non-ASCII/non-Latin rates per country, top-30 name/address tokens per country, on student_resource/dataset/test/test_source{1,2,3}.tsv via legacy/src/phase0_summary.py.
- WHY: confirm France present structurally; check normalization will not break on French text.
- FORBIDDEN (not done): no matching/scoring against test, no threshold/feature tuning on test, no rules from specific test rows, no hand-labeling.
- ARTIFACT: artifacts/metrics/test_inspection.json

## 2026-09-25 Bucketing diagnostic (writing-system census)
- WHAT: per-country writing-system class counts (ascii / latin_ext / mixed / nonlatin / empty) for name and address, dominant non-Latin script, count of fields that normalize_*() erases to "", and letters dropped by normalization, on test_source{1,2,3}.tsv via legacy/src/diag_scripts.py.
- WHY: character-set check (C7-allowed category) to confirm whether normalization/tokenization breaks on test text (France and native-script India names).
- FORBIDDEN (not done): no matching/scoring against test, no tuning on test, no rules from specific test rows.
- ARTIFACT: artifacts/metrics/diag_scripts.json (keys test_S1/test_S2/test_S3)
