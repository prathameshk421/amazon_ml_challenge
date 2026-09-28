# Deferred issues (observe-only, not fixed)

Per user instruction (chat, 2026-09-25, ~9:10pm): while `candidates --set TEST` runs (~2h) and the
team focuses on getting a first submission out with the matcher, any problem found in the bucketing
pipeline is logged here, NOT fixed, until the user says otherwise. Format: what, where, why it might
matter, suggested fix (not applied).

## No intermediate progress reporting in `candidates`/`generate_candidates`
- Where: `src/ber/rerank.py::generate_candidates` (used by both `run_candidates.py` and `run_rerank_eval`).
- What: results from `QueryRunner.map()` are accumulated into `pool_lists`/`rank_lists`/`p_lists` in
  memory across the whole query set and `write_candidates` is called once at the end. There is no
  per-chunk progress log line, so a long run (e.g. `candidates --set TEST`, ~1.73M queries) gives no
  way to see how many queries are actually done short of elapsed-time estimation.
- Why it might matter: makes it hard to tell "still working normally" from "stuck" on a long run, and
  a crash near the end loses all progress (nothing is flushed incrementally).
- Suggested fix (not applied): log a line every N chunks (queries processed / total, elapsed, ETA) in
  the `qr.map(...)` loop inside `generate_candidates`; optionally flush `write_candidates` per outer
  chunk instead of once at the end, so a crash keeps partial progress (candidates/ already supports
  resumable parts via `_candidates_ready`, this would just mean writing them incrementally instead of
  all at once).

## Stage-2 re-ranker: zero-padded numbers read as postal codes (2026-09-26)
- Where: `src/ber/rerank.py::_postal_tokens` / `compute_features` (`postal` feature).
- What: pool addresses zero-pad house/door numbers (`0412 brunswick dr`, `door no 0381`). A 4-digit
  zero-padded house number passes the 4-6 digit postal test, and `0412` never equals the S1's `412`.
  The stage-3 matcher had the same defect in its number features; there it is fixed (`match._canon_num`;
  2.7% of MATCH_VALID true pairs with numbers on both sides shared a number only after stripping zeros).
- Why not fixed here: changing a stage-2 feature means rerank-build/train/cut and regenerating every
  candidate set (TEST alone 8,463 s). Bundle it with the next stage-2 retrain.
- Suggested fix: canonicalize digit tokens (`t.lstrip("0") or "0"`) before `_postal_tokens` and compare.

## Stage-2 re-ranker stopped at the round cap (2026-09-26)
- `rerank_train.json`: best_iteration 400 = num_boost_round 400; early stopping never fired.
- Effect unmeasured. Measure first: retrain with num_boost_round 3000 (early stopping 50) into a separate
  model file and compare RR_CAL logloss and the F0.5 ceiling at the chosen cut. With K_min 20 the ceiling
  is within 0.0001 of stage 1 (`rerank_cut.json`), so any gain would come through `p_rerank` as a
  matcher feature, not through recall.
