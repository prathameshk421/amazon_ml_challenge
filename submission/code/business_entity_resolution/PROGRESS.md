# PROGRESS
LAST_UPDATE: 2026-09-25T15:50:18+0530
CURRENT: P3.1 build-index --split train
## Phases
P0 setup + goldens + tests: DONE (Unicode 16.0.0, pins match §3.1; 86 unit tests pass incl. all 83 goldens)
P1 ingest + splits: DONE (ingest_train.json, ingest_test.json; canonical S1 files are train_source1_train.tsv / train_source1_validation.tsv next to the dataset — 1,765,458 / 441,363, country × singleton; S2+S3 unsplit)
P2 textnorm (E0) + dictionary: DONE (e0_abbrev.json adopt; translit_dict.json gate pass; normalize_train.json)
P3 train index:
P4 stage-1 (E1–E6):
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
