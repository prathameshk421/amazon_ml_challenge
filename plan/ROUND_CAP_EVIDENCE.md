# LightGBM round cap (`num_boost_round`): measured evidence, not a guess

Status: reference, 2026-09-26. Read this before setting `num_boost_round`/`ROUND_BUDGET` for any stage-3
matcher training run, at any data scale. Every number below cites its `artifacts/metrics/*.json` or a run
log — no number here is estimated.

## The mistake this file exists to prevent

Twice in one session, a fixed round cap was set from the *previous* scale's experience and turned out to
be too low at the next scale up:
- `dev_rest_180k.py` used the shipped default `num_boost_round=3000` (fine at 180,000 S1) on a 360,000-S1
  combined run — 2 of 5 folds hit the cap without converging (`best_iteration` 2997 and 3000, `work/logs/dev_rest_180k.log`).
- `dev_rest_full.py` then raised the cap to 4000, reasoning only "the 360k run needed more than 3000" — at
  1,655,458 S1, 3 of 3 folds completed so far hit the cap again (`best_iteration` 4000, 3998, 3988,
  `work/logs/dev_rest_full.log`). The fix from the last scale was still too small for this one.

The pattern: **a round cap sized for one data scale is not safe to assume at the next scale.** This file
is the fix — a measured table, and a mechanical check to run after every training, not another guess.

## Measured data: `best_iteration` per fold, all at `learning_rate=0.05` (unchanged across every run below)

| Run | Total rows | Fit rows/fold (~72% of total) | Cap | `best_iteration` per fold | Any fold hit the cap? |
|---|---|---|---|---|---|
| k5_base (180,000 S1) | 975,699 | ~702,500 | 3000 | 2085, 1997, 1936, 1849, 1891 | No |
| k5_feat (180,000 S1) | 975,699 | ~702,500 | 3000 | 1448, 1703, 1927, 1901, 1724 | No |
| x1_strsim (180,000 S1) | 975,699 | ~702,500 | 3000 | 1651, 1819, 2011, 1908, 1574 | No |
| dev_rest_180k (360,000 S1) | 1,952,601 | ~1,405,900 | 3000 | 2997, 2424, 2566, 2727, **3000** | Yes, 2 of 5 |
| dev_rest_full (1,655,458 S1) | 8,979,983 | ~6,465,600 | 4000 | **4000**, **3998**, **3988**, (2 folds still running) | Yes, 3 of 3 so far |

Source files: `artifacts/metrics/match_train_{k5_base,k5_feat,x1_strsim}.json` (`folds[].best_iteration`),
`work/logs/dev_rest_180k.log`, `work/logs/dev_rest_full.log`.

## What this evidence actually supports, and what it doesn't

**Supported (a):** at a fixed learning rate, the number of rounds needed to converge rises as training
data grows, and the safe cap at one scale is not automatically safe at the next. The 180,000-S1 runs never
came close to their 3000 cap (max 2085); by 1,655,458 S1 every fold measured so far needed *more* than
4000.

**Not supported — do not over-fit a formula to two noisy points:** the 360,000-S1 run shows real
per-fold variance (2424 to 3000+ within the same run, same data scale) — which S1 happen to land in a
fold visibly affects how many rounds it needs, not just the row count. Do not compute a clean
multiplier (e.g. "rounds scale linearly with rows, so multiply by 9.2x") and trust it blindly. The
right level of confidence here is "rounds-needed grows with data size, roughly, with real fold-to-fold
noise" (c), not a precise predictive formula (that would be (d), a guess dressed as a measurement).

## The actual rule to follow (mechanical, not a guess)

1. **Never trust a training run without checking `best_iteration` against the cap for every fold.** If
   any fold's `best_iteration >= num_boost_round - early_stopping_rounds`, that fold did not converge —
   it was truncated, not early-stopped. Its OOF prediction is optimistic-in-the-wrong-direction
   (undertrained, likely worse than the model's true capability at that data size), not simply "a
   slightly worse but valid measurement."
2. **When starting a run at a new data scale, do not assume the previous scale's cap.** Start from this
   table's largest comparable point and go meaningfully higher, or use `hparam_search.py`'s
   `round_cap()`/retry-at-2x-cap logic (`plan/checks/hparam_search.py`, reviewed 2026-09-26) rather than a
   fixed number: it scales the cap by `learning_rate` and automatically retries a truncated fold at 2x the
   cap once before flagging it as still-truncated. That logic accounts for the learning-rate axis; combine
   it with a data-size-aware starting point from this table for the row-count axis, since the two effects
   are independent and this table only has evidence for the row-count one.
3. **After any run, append its `best_iteration` values to the table above**, with its own metrics file
   cited, before drawing a conclusion from its F0.5. If a fold hit the cap, say so explicitly next to the
   headline number, the way this file's own MATCH_ALL entry does — do not report a capped run's F0.5 as if
   it were the model's converged best.
4. **If a whole training set (`MATCH_ALL`, ~8.98M rows) will be trained again, allocate a much higher cap
   from the start** — the current dev_rest_full.py run at cap 4000 hit it on every fold measured so far,
   so a rerun should start at least 2-3x that (8000-12000) and still verify against rule 1, not assume
   that number is enough either.

## Open, unmeasured

- No fold at any scale in this table has been allowed to run to full, uncapped convergence — every "hit
  cap" fold's true convergence point is unknown, only bounded below by the cap it hit. This means the true
  shape of the rows-vs-rounds relationship is not yet known past the point where the cap starts binding.
- Whether the relationship is closer to linear, sub-linear (e.g. sqrt), or something else in rows has not
  been measured — the two available scale-up points are too few and too noisy (see above) to fit a curve.
