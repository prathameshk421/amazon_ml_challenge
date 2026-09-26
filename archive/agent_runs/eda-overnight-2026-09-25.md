# EDA OVERNIGHT

*Exported on 2026-09-25*

---

**User**

*Sep 25, 2026, 09:08*

continue

---

**User**

*Sep 25, 2026, 13:09*

how much progress was done

---

**Assistant**

*Sep 25, 2026, 13:09 (opencode/muse-spark-1.3-contributor-free)*

Progress so far:

- **Phase 0 DONE**: metric harness (unit-tested), fit/val split (seed 42), data integrity verified (S1==GT ID sets, all 7.6M GT links in pool, each pool record ≤1 owner).
- **Phase 1 DONE**: full EDA report — 17 signals ranked (address signals dominate hard negatives; TF-IDF best name signal; phonetic US-only), normalization v1 built from train frequencies, noise catalog with real examples. Key structural finding: 40% of S1 entities share names (chains), 26% of pool are orphans.
- **Phase 2 DONE**: blocking evaluated, recommended config = ranked idf-union top-150 (pair recall 0.922, entity recall 0.987, 1.7ms/query). Candidates generated for 60K fit-sample + full val (441K). BK-tree rejected for full pool (too slow); phonetic adds ~0 to blocking.
- **Phase 3 partial**: 19 features, TF-IDF fit, 9M training pairs featurized, LightGBM trained — OOF F0.5 **0.9052** (t=0.62); uniform negatives beat hard-upweighting (0.9063 vs 0.9050, negative result). Model saved.
- **Stuck now**: val scoring (66M pairs) died silently ~2h in with no output — likely OOM in workers. No val F0.5 yet, so Phases 3 (val/rules/ablation/LOCO), 4, 6 remain.

Next: relaunch val scoring with smaller batches + chunked TF-IDF transforms to stay under memory limits.

---

**User**

*Sep 25, 2026, 13:15*

should I use google collab tpu for training and everything? or i have a friend with laptop rtx 4070 8gb , 24gb ram , i7 14th gen , what should I do

---

**Assistant**

*Sep 25, 2026, 13:15 (opencode/muse-spark-1.3-contributor-free)*

Use your friend's laptop. Skip the TPU — it helps you zero here.

Why:

- **Nothing in this pipeline runs on a TPU.** The workload is LightGBM, sklearn, rapidfuzz, pandas, and inverted-index joins — all CPU code. TPUs only accelerate JAX/TensorFlow/PyTorch-XLA programs. Sentence-transformers on TPU is a painful science project, not a speedup.
- **Your actual bottlenecks are RAM and CPU cores, not GPU.** The val-scoring job just died from memory pressure on 17GB RAM. Your friend's 24GB RAM + i7-14th-gen (likely 20 cores) directly fixes that and roughly doubles featurization/blocking throughput.
- **The RTX 4070 helps exactly one thing: Phase 5 embeddings.** Encoding ~10M records and contrastive fine-tuning of a small embedder (arctic-embed-xs, MiniLM) is 5–10× faster on a 4070 than on Mac CPU/MPS. 8GB VRAM is enough for these small models with modest batch sizes. The LightGBM matcher itself won't care about the GPU.

Caveats before you move:

1. **Windows breaks your code.** The pipeline uses `multiprocessing` with fork (no Windows fork). Run it under WSL2 Ubuntu, or budget 30 min to switch to spawn-safe pooling.
2. **Moving machines costs an hour** (OS setup, venv, copying 2.5GB data + ~3GB index, re-validating). The Mac can still finish the current compressed run — the immediate fix is smaller batches, which is already in progress.
3. **Colab free tier as fallback for embeddings only** — fine for a quick encoding experiment, but 12h timeouts, ~100GB disk cap with your artifacts, and re-uploading data make it worse than either local option for the full pipeline.

Verdict: finish the baseline on the Mac, then port to the friend's laptop (WSL2) for embedding exploration and any scale-up (K=250 candidates, full-fit training).