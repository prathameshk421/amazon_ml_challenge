# PROGRESS
LAST_UPDATE: 2026-09-25T19:08:29+0530
CURRENT: P5.1 rerank-build (stage-2 re-ranker)
## Phases
P0 setup + goldens + tests: DONE (Unicode 16.0.0, pins match §3.1; 86 unit tests pass incl. all 83 goldens)
P1 ingest + splits: DONE. Canonical split = teammate's data/write_s1_split.py output (train_source1_train.tsv 1,765,458 / train_source1_validation.tsv 441,363, seed 42, country×singleton strata) — this supersedes the plan's own §5.4 RNG split per AGENTS.md priority (AGENTS.md > split.md > BUCKETING_PLAN.md). splits.py reproduces it exactly (verified: computed HOLDOUT_TEST/val-S1 entity-id set == train_source1_validation.tsv, byte-for-byte). DEV_A/DEV_B/S1R_TRAIN/RR_TRAIN/RR_CAL/MATCH_TRAIN/MATCH_VALID/DEV_REST/DICT_SRC are internal work-slices drawn only from the teammate's train_ids (perm seed 20260925), so validation-S1 ground truth is never touched by tuning.
P2 textnorm (E0) + dictionary: DONE — re-run against the corrected split (first run used a stale pre-teammate-split DEV_A/DICT_SRC, discarded; see Deviations). E0 adopt (true rise 0.0588 vs negative 0.0013). Dictionary gate 0.2701→0.4491 pass (445 name / 902 addr entries).
P3 train index: DONE (index_train.json; 11 families incl. SK; index-sanity 3078/3078 = 1.0; rebuilt after the split correction, 805.2s)
P4 stage-1 (E1–E6): DONE on real DEV_A/DEV_B (s1_E1..E6.json)
P5 stage-2:
P6 val-S1 (once) + test index + outputs:
## Results (one line each, citing a metrics json)
- E0: address-token Jaccard of DEV_A true pairs 0.6970 → 0.7534 (+0.0564) vs random negatives +0.0012 → 11b adopted (e0_abbrev.json; maps in work/norm/abbrev_train.json)
- Dictionary gate: DEV_A usable-token share 0.2896 → 0.4847, every script up (Tamil 0.165 → 0.553); 445 name / 888 addr entries (translit_dict.json). §5.3 cited ≈0.26 → ≈0.61 from an unrerun critique measurement; the gate rule itself passes.
## BLOCKERS
## Deviations (what, why, approved-by)
- Code lives in `submission/code/business_entity_resolution/` instead of `code/business_entity_resolution/` at the repo root, so the submission folder can be zipped directly. approved-by: user (chat, 2026-09-25)
- Full P1–P6 run on the Mac (8 cores, 16 GB; W = min(14, 8−2) = 6) instead of the laptop. approved-by: user (chat, 2026-09-25)
- Experiment commands write their decisions into `configs/blocking.json` (with `tuned_by`). approved-by: user (chat, 2026-09-25)
- `requirements.txt` = the §3.1 pin list (identical to the Mac venv versions) instead of `pip freeze` of the Mac venv, which also holds EDA-only packages. approved-by: pending
- Added CLI command `abbrev-e0` (the runbook lists E0 in P2 but names no command). approved-by: pending
- Plan vs reference (code wins, R1 header): §9 idempotence holds only for addresses; the reference name normalizer is not idempotent (`C)O` → `co` → `company`), so the idempotence test covers addresses only. approved-by: n/a (normative code)
- Plan vs reference: §9 example `rd`/`road` cannot be mined because `rd` is an ADDR_ABBREV key (§5.2.2 step 6 drops it); the test plants `rte`/`route`. approved-by: n/a
- `plan/checks/abbrev_miner.py` mined on steps 1–10 with ADDR_ABBREV emptied; §5.2.2 says steps 1–11 → implemented 1–11. approved-by: n/a (plan text)
- E0: pairs where either normalized address is empty are skipped (as `plan/checks/norm_v21_check.py`). approved-by: user (chat, 2026-09-25)
- §5.9 pool-side segments (pool name class, pool address empty): a query belongs to segment X if ≥ 1 of its true pool records has X; all query metrics on those queries + pair recall over the true pairs with X. approved-by: user (chat, 2026-09-25)
- E2: each candidate family tested independently as E1 set + F vs E1 set; kept set = E1 ∪ kept F; PH removal tested on the kept set; exclusive pairs = true pairs in the union reachable only via F. approved-by: user (chat, 2026-09-25)
- E5 "best" = highest overall F0.5 ceiling among settings meeting both conditions (ties: smaller mean size). approved-by: user (chat, 2026-09-25)
- learn-dict: a pool token counts once per distinct token per pair (as plan/critique/scripts/d_evidence.py); gate "after" recomputes train-pool df with the dictionary applied to Indic-name records. approved-by: n/a (prototype detail)
- BLOCKER caught and fixed: a teammate published the canonical S1 train/validation split (`data/write_s1_split.py`, `data/student_resource/dataset/train/split.md`) after P1/P2 had already run once using this pipeline's own §5.4 RNG split. Under the new AGENTS.md that split is authoritative and validation-S1 labels are scoring-only. The stale run's DEV_A/DICT_SRC (used by E0 and the transliteration dictionary) were not guaranteed disjoint from the teammate's validation-S1, so both were re-run from a regenerated `splits/query_sets.json` built on the teammate's split before continuing. approved-by: user (chat, 2026-09-25, "just use my teammates split and all, forgot about ur split and start using it")
- `data/` (the workspace's dataset copy + split script) added to `.gitignore`; dataset is read-only, never uploaded. approved-by: user (chat, 2026-09-25)
- Bug found + fixed: `index_build.build_split_index`'s per-family resume/skip only checked structural validity of existing files, not whether the input norm pool parquet had actually changed. A `build-index` re-run after re-normalizing (e.g. after the split correction above) silently kept the stale index (observed: second run finished in 46s instead of ~805s, logging "files verify, skipped" for every family). Fixed by fingerprinting the norm pool file (size + mtime_ns, stored in meta.json as `norm_input_fingerprint`); a mismatch forces a full rebuild of every family regardless of structural validity. Re-verified: forced rebuild after the fix took 805.2s (matching the original full build) and index-sanity passed 3078/3078. approved-by: n/a (correctness bug)
- P4 results (DEV_A 10,000 queries unless noted; all from artifacts/metrics/s1_E*.json):
  - E1 gate: families {EN,NT,NG,PH,AT}, pair_recall@150 = 0.9374 (≥ 0.91 gate; old system 0.9251 on a different split/normalization).
  - E2: kept EN,NT,NG,NP,SP,NC,AT,AB,XK (PH dropped: kept-PH f05 0.9960 vs kept 0.9961, under the +0.001 keep bar; SK excluded, no exclusive-pair or f05 gain).
  - E3: NT cap 0.002→0.001 (f05 loss 0.0001 < 0.0005, ms p50 fell 15.0% ≥ 15%); NG/AT/NP/SP/AB/XK unchanged (no cap in {0.5,1,2.5}x met either threshold).
  - E3b: stage1-train on S1R_TRAIN (12,003,851 rows, 69,257 positives, 20,000 queries) converged in 12 iters/33.3s; learned top300 f05 0.9922 ≥ hand_both top300 f05 0.9779 → LEARN channel kept as stage1_model.
  - E4: 486-config quota grid; chosen LEARN150/NAME0/ADDR50/PAIR100/XK50/CAT20, f05 0.9957, mean size 291.0, entity recall 0.9993, pair recall 0.9854 (best on the grid: f05 0.9966 at mean 741).
  - E5: chain rule off (no {min_chain,mult} setting reached +0.005 chain≥10 f05 gain within +15% mean-size growth).
  - E6 (DEV_B, 10,000 queries): f05 0.9955 vs DEV_A 0.9957 (Δ −0.0002, within the −0.003 tolerance) → chosen config confirmed, no Pareto fallback needed.
- Bug found + fixed: `tests/test_translit_dict.py::TestEndToEnd` read the live `configs/blocking.json` cap_frac.NT and its synthetic fixture size was hand-calibrated to the *original default* 0.002 (comment: "cap = floor(0.002 * 6013) = 12"). After E3 tuned cap_frac.NT to 0.001 on real data, the test started failing (0 usable tokens, gate reads pass=False) — a real config-coupling bug, not a code bug. Fixed by pinning cfg["cap_frac"]["NT"] = 0.002 in the test's setUp regardless of what real tuning has since written to blocking.json. approved-by: n/a (test-isolation bug)
