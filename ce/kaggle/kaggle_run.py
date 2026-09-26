"""Kaggle kernel driver for ce_rec_base (one file, one job per kernel; see ce/kaggle/README.md).

  JOB=probe | train_score | score_rest   (set by the kernel folder's copy of this file, see README)

Inputs are found by globbing /kaggle/input (mount paths differ between Kaggle versions):
  pairs dataset   -> the folder holding pairs_MATCH_VALID.parquet and the ce/*.py scripts (flat)
  K2 output (score_rest only) -> the folder holding ce_rec_base/model/config.json
Checkpoint: BAAI/bge-reranker-base (MIT) downloaded from the Hugging Face hub at a pinned revision into /tmp
(not saved as output). That download is the only network use; training and scoring are offline.
Outputs go to /kaggle/working/ce_rec_base/ (kept by "Save Version", downloaded with `kaggle kernels output`).
"""
import glob
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

JOB = os.environ.get("JOB", "__JOB__")
CKPT_REPO = "BAAI/bge-reranker-base"
CKPT_REV = "2cfc18c9415c912f9d8155881c133215df768a70"
CKPT_FILES = ["config.json", "model.safetensors", "sentencepiece.bpe.model", "special_tokens_map.json",
              "tokenizer.json", "tokenizer_config.json"]
W = Path(os.environ.get("CE_WORK", "/kaggle/working"))  # EC2: CE_WORK/CE_INPUT env
INPUT = os.environ.get("CE_INPUT", "/kaggle/input")
OUT = W / "ce_rec_base"


def find(pattern):
    hits = sorted(glob.glob(f"{INPUT}/**/{pattern}", recursive=True))
    if not hits:
        raise SystemExit(f"input not found: {pattern}")
    return Path(hits[0]).parent


def checkpoint():
    from huggingface_hub import snapshot_download
    d = snapshot_download(CKPT_REPO, revision=CKPT_REV, local_dir="/tmp/bge-reranker-base", allow_patterns=CKPT_FILES)
    return Path(d)


def sh(*args, env=None):
    print(">>>", " ".join(map(str, args)), flush=True)
    subprocess.run([sys.executable, *map(str, args)], check=True, env=env)


def score_parallel(scripts, pairs, model, out, set_name, n_gpu):
    """One process per GPU on row shards, then merge in pair-file order and drop the parts."""
    procs = [subprocess.Popen([sys.executable, str(scripts / "inference.py"), "--pairs", str(pairs), "--model",
                               str(model), "--out", str(out), "--set", set_name, "--shard", f"{k}/{n_gpu}",
                               "--gpu", str(k)]) for k in range(n_gpu)]
    if any(p.wait() for p in procs):
        raise SystemExit(f"scoring {set_name} failed")
    sh(scripts / "inference.py", "--pairs", pairs, "--out", out, "--set", set_name, "--merge")
    shutil.rmtree(out / "parts" / set_name, ignore_errors=True)


def main():
    import torch
    n_gpu = max(torch.cuda.device_count(), 1)
    print("job", JOB, "gpus", [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())], flush=True)
    pairs = find("pairs_MATCH_VALID.parquet")
    scripts = pairs  # ce/*.py are uploaded flat next to the pair files
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    ckpt = checkpoint() if JOB in ("probe", "train_score") else None

    if JOB == "probe":
        sh(scripts / "probe.py", "--pairs", pairs, "--model", ckpt, "--out", OUT, "--n-gpus-scoring", n_gpu)
        # exercise every code path k2 uses, at toy size: train.py save, inference.py shards + merge
        smoke = W / "smoke"
        sh(scripts / "train.py", "--pairs", pairs, "--model", ckpt, "--out", smoke, "--limit", 3000,
           "--max-steps", 30, "--eval-every", 30)
        score_parallel(scripts, pairs, smoke / "model", smoke, "MATCH_VALID", n_gpu)
        shutil.rmtree(smoke / "model")  # keep train_meta.json + MATCH_VALID.parquet as evidence, not weights

    elif JOB == "train_score":
        # K1 smoke: loss must fall and held-out AUC must beat the untrained model, else stop before the real run
        smoke = W / "smoke"
        sh(scripts / "train.py", "--pairs", pairs, "--model", ckpt, "--out", smoke, "--limit", 20000,
           "--max-steps", 150, "--eval-every", 150)
        import json
        m = json.load(open(smoke / "train_meta.json"))
        print("smoke before", m["before"], "after", m["best"], flush=True)
        if not m["best"]["auc"] > m["before"]["auc"]:
            raise SystemExit("smoke run: held-out AUC did not improve over the untrained model")
        shutil.rmtree(smoke)
        # K2: full run
        sh(scripts / "train.py", "--pairs", pairs, "--model", ckpt, "--out", OUT)
        # untrained reference on MATCH_VALID (for ce/evaluate.py), then the fine-tuned model on every set
        score_parallel(scripts, pairs, ckpt, W / "untrained_base", "MATCH_VALID", n_gpu)
        for s in ("MATCH_VALID", "MATCH_TRAIN", "TEST"):
            score_parallel(scripts, pairs, OUT / "model", OUT, s, n_gpu)
            print(f"elapsed {(time.time() - t0) / 3600:.2f} h", flush=True)

    elif JOB == "score_rest":
        prev = find("ce_rec_base/model/config.json")  # K2 kernel output attached as input
        score_parallel(scripts, pairs, prev, OUT, "DEV_REST_REST", n_gpu)

    else:
        raise SystemExit(f"unknown JOB {JOB!r}")
    print(f"done {JOB} in {(time.time() - t0) / 3600:.2f} h", flush=True)


if __name__ == "__main__":
    main()
