# Licenses (source: artifacts/metrics/licenses.json via legacy/src/collect_licenses.py, offline pip metadata)

| lib | version | license |
|---|---|---|
| pandas | 3.0.6 | BSD (OSI Approved) |
| numpy | 2.5.3 | BSD-3-Clause (+bundled 0BSD/MIT/Zlib/CC0-1.0) |
| scikit-learn | 1.9.1 | BSD-3-Clause |
| scipy | 1.18.1 | BSD (OSI Approved) |
| rapidfuzz | 3.14.6 | MIT |
| jellyfish | 1.2.1 | MIT |
| lightgbm | 4.7.0 | MIT |
| xgboost | NOT INSTALLED | n/a (not used) |
| pytest | 9.1.1 | MIT (dev-only: test runner, not used in training/inference) |
| sentence-transformers | 6.1.0 | Apache-2.0 |
| torch | 2.14.0 | Apache-2.0 (+ LLVM-exception/BSD/BSL-1.0/MIT components) |
| transformers | 5.17.0 | Apache 2.0 |
| huggingface-hub | 1.33.0 | Apache Software License |
| matplotlib | 3.11.2 | PSF License (matplotlib agreement) |
| tqdm | 4.70.1 | MPL-2.0 AND MIT |
| pyarrow | 25.0.1 | Apache-2.0 |
| git-lfs | 3.8.0 | MIT |

Models: none downloaded yet (Phase 5). Allowed: Snowflake/snowflake-arctic-embed-xs (Apache-2.0),
sentence-transformers/all-MiniLM-L6-v2 (Apache-2.0), BAAI/bge-small-en-v1.5 (MIT) — license to be
verified on the model card via huggingface_hub at download time and logged here.

## Cross-encoder (Kaggle run `ce_rec_base`, 2026-09-26)

| item | version | license | use |
|---|---|---|---|
| BAAI/bge-reranker-base | rev 2cfc18c9415c912f9d8155881c133215df768a70, 278M params | MIT (model card tag `license:mit`) | cross-encoder fine-tuned on DEV_REST_180K pairs; offline, run with internet off |
| kaggle (CLI) | 2.2.4 | Apache-2.0 | upload private datasets / push kernels; tooling only, not in training or inference code |
| Kaggle image torch / transformers | recorded per run in `train_meta.json` | Apache-2.0 | training/scoring runtime on Kaggle T4 |

## Cloud GPU box (AWS EC2, `cloud/`, `scripts/`, 2026-09-26)

| item | version | license | use |
|---|---|---|---|
| AWS Deep Learning AMI GPU PyTorch 2.14 (Ubuntu 26.04) | ami-0bd62606c5fd07f72 (20260924, ap-south-1) | AWS DLAMI terms; bundled torch Apache-2.0-style BSD | GPU runtime (driver, CUDA, torch) |
| accelerate | resolved on first install, `/workspace/logs/pip_freeze.txt` | Apache-2.0 | sentence-transformers CrossEncoder trainer dependency |
| datasets | same | Apache-2.0 | trainer input format |
| evaluate | same | Apache-2.0 | installed on request; not used by our metric code (per-S1 F0.5 is ours) |
| cross-encoder/ms-marco-MiniLM-L6-v2 | hub latest at first download | Apache-2.0 | smoke test on synthetic pairs; baseline candidate only |
| runpod (Python SDK) | 1.12.0 | MIT | local-only: create/terminate the GPU pod for the cross-encoder job (`ce/runpod/launch.py`); never imported by training/inference code |
| runpod/pytorch container image | tag in `ce/runpod/launch.py` | Runpod image; bundled torch BSD-3 | GPU runtime on the pod |
