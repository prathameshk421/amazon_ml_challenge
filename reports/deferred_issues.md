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
