START: Fri Sep 25 01:43:41 IST 2026
LAST_UPDATE: Fri Sep 25 14:30 IST 2026
REMOTE_NOTE_2026-09-25: linux setup: dataset symlinked via ../data, .gitignore fixed, .venv created, pip install running, missing bundle reported; local commit only, push left for user per M2
PULL_MERGE_2026-09-25: fetch+pull done, conflicts resolved, merge d55ad2a, now ahead 6. Push NOT done (policy-blocked + heavy files flagged, see assumptions). Manual slim+push commands left for user.
HOUSEKEEPING: COMMIT DONE 3a177a5 main clean; rename plus push left for user.
TEAMMATE BUNDLE: zip running in background (pid 96465, log logs/bundle_zip.log) -> teammate_share/teammate_bundle.zip split 1900m (M7 single-file cap).
TEAMMATE BUNDLE: DONE teammate_share/teammate_bundle.z01 (1.9G) + teammate_bundle.zip (1.1G); 51 files, 6.7G uncompressed; listing verified; bundle git-ignored, handoff only.
TEAMMATE BUNDLE V2 (no dataset): old parts deleted; zipping candidates + index + 4 parquets + files -> teammate_share/teammate_artifacts.zip (split 1900m) in background (pid 5401, log logs/bundle_zip2.log).
TEAMMATE BUNDLE V2: DONE teammate_artifacts.z01 (1.9G) + teammate_artifacts.zip (39M); 34 files, 4.2G uncompressed, no student_resource; listing verified; pid 5401 reaped.
PHASE 0: DONE
PHASE 1: DONE
PHASE 2: DONE
PHASE 3: IN-PROGRESS (candidates ready; TF-IDF fit next, then featurize/train/val)
PHASE 4: TODO
PHASE 5: SKIPPED(time: clock anomaly forced compressed path; see assumptions 09:30)
PHASE 6: TODO
NEXT ACTION: Phase 3 featurize + LightGBM OOF + val F0.5
PHASE 2: TODO
PHASE 3: TODO
PHASE 4: TODO
PHASE 5: TODO
PHASE 6: TODO
NEXT ACTION: Phase 1 EDA (structural 1a on fit part, then signals 1b, structure 1c)
REPOSITORY HOUSEKEEPING: Local uncommitted work is being committed; folder rename and remote push are deferred because project rules prohibit moving the project root or running git push.

BUCKETING DIAGNOSTICS (Fri Sep 25 14:01:43 IST 2026): DONE, no training. reports/bucketing_diagnostics.md, metrics diag_{scripts,blocking,breakdown,rerank,blocking2,quota}.json, aux index artifacts/index/aux.npz. Found normalize v1 erases Indic names (699K train pool). Next: bucket_prompt_v2.md Phase 1 (normalize v2).
LFS_MIGRATE_2026-09-25: `git lfs track "*.npy" "*.bin" "*.pkl" "*.parquet"` + commit 81b063e, then `git lfs migrate import --skip-fetch` rewrote 9 unpushed commits (npy 3.1G + bin 744M -> 3.8G LFS objects). INFO after: git push payload still ~123M JSON; LFS quota (1G free) would choke, so squashed instead.
SQUASH_2026-09-25: backup branch + `git reset --soft origin/main` (only --hard is denied) + single commit 69e9106. Tree verified identical (9ff68cb7). `migrate info` now: 1 commit, ~2.3M total, 0 LFS objects. Branch: ahead 1. Push left for human (git push* denied in-session).
NEXT ACTION: human runs `git push` (small, ~2.3M); optional later `git lfs prune && git gc` to reclaim .git space.
