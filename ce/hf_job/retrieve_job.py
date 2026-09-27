"""Bi-encoder retrieval (gate 1 of plan: retrieval recall channel): multilingual-e5-small embeddings of every pool
record and of each query, then per-country exact top-k by cosine (GPU matmul, no index).

Inputs (HF dataset REPO, or local dir with RETR_LOCAL=<dir>):
  retrieval/<TAG>_pool.parquet     pool_idx:uint32, country:str, text:str
  retrieval/<TAG>_queries.parquet  qid:int64, kind:str ('s1' | 'seed'), country:str, text:str, self_pool:int64 (-1 for s1)
Output: retrieval/<TAG>_topk.parquet  qid, rank:int16, pool_idx:uint32, cos:float16   (seed rows skip self_pool)

  hf jobs run --flavor a100-large ... -e RETR_TAG=gate1 python retrieve_job.py
Model: intfloat/multilingual-e5-small (MIT). Text is "query: <name> | <address>" on both sides (symmetric task, e5 card);
mean pooling over the attention mask, L2-normalised.
"""
import os
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import torch

REPO = os.environ.get("CE_REPO", "prathameshk421/ber-ce-scoring")
TAG = os.environ.get("RETR_TAG", "gate1")
LOCAL = os.environ.get("RETR_LOCAL")
MODEL = "intfloat/multilingual-e5-small"
MODEL_DIR = os.environ.get("RETR_MODEL_DIR")  # subfolder of REPO with fine-tuned weights (e.g. e5_distil)
OUT_TAG = os.environ.get("RETR_OUT_TAG", TAG)
QTAG = os.environ.get("RETR_QUERY_TAG", TAG)  # queries file tag (pool file always from TAG)
K = int(os.environ.get("RETR_K", "50"))
MAX_LEN = int(os.environ.get("RETR_MAX_LEN", "64"))
BATCH = int(os.environ.get("RETR_BATCH", "1024"))
QCHUNK = int(os.environ.get("RETR_QCHUNK", "1024"))  # 1024 x 6.2M fp16 = 12.7 GB

t_job = time.time()
if LOCAL:
    root = Path(LOCAL)
else:
    from huggingface_hub import snapshot_download
    root = Path(snapshot_download(REPO, repo_type="dataset", local_dir="/tmp/retr_in",
                                  allow_patterns=[f"retrieval/{TAG}_pool.parquet", f"retrieval/{QTAG}_queries.parquet"]
                                  + ([f"{MODEL_DIR}/*"] if MODEL_DIR else [])))
    if MODEL_DIR:
        MODEL = str(root / MODEL_DIR)
root = root / "retrieval" if (root / "retrieval").exists() else root
dev = torch.device("cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"))
dtype = torch.bfloat16 if dev.type == "cuda" else torch.float32
print(f"device {dev} {torch.cuda.get_device_name() if dev.type == 'cuda' else ''}", flush=True)

from transformers import AutoModel, AutoTokenizer  # noqa: E402
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModel.from_pretrained(MODEL, dtype=dtype).to(dev).eval()


@torch.inference_mode()
def embed(texts, tag):
    """(n, 384) float16 on the device, L2-normalised; batches sorted by length to limit padding."""
    order = np.argsort([len(t) for t in texts], kind="stable")
    out = torch.empty((len(texts), model.config.hidden_size), dtype=torch.float16, device=dev)
    t0 = time.time()
    for i in range(0, len(texts), BATCH):
        idx = order[i:i + BATCH]
        b = tok([texts[j] for j in idx], padding=True, truncation=True, max_length=MAX_LEN, return_tensors="pt").to(dev)
        h = model(**b).last_hidden_state
        m = b["attention_mask"].unsqueeze(-1).to(h.dtype)
        e = torch.nn.functional.normalize((h * m).sum(1) / m.sum(1), dim=-1)
        out[torch.as_tensor(idx, device=dev)] = e.to(torch.float16)
        if (i // BATCH) % 1000 == 0:
            done = min(i + BATCH, len(texts))
            print(f"[{tag}] {done:,}/{len(texts):,} ({done / (time.time() - t0):.0f}/s)", flush=True)
    print(f"[{tag}] {len(texts):,} embedded in {time.time() - t0:.0f}s", flush=True)
    return out


pool = pq.read_table(root / f"{TAG}_pool.parquet")
qs = pq.read_table(root / f"{QTAG}_queries.parquet")
P = embed(pool.column("text").to_pylist(), "pool")
Q = embed(qs.column("text").to_pylist(), "queries")
p_idx = pool.column("pool_idx").to_numpy()
p_cty = np.asarray(pool.column("country").to_pylist(), dtype=object)
q_cty = np.asarray(qs.column("country").to_pylist(), dtype=object)
q_id = qs.column("qid").to_numpy()
q_self = qs.column("self_pool").to_numpy()

cols = {"qid": [], "rank": [], "pool_idx": [], "cos": []}
for c in sorted(set(q_cty.tolist())):
    qi = np.flatnonzero(q_cty == c)
    pi = np.flatnonzero(p_cty == c)
    if pi.size == 0:  # a country absent from the pool: search the whole pool
        pi = np.arange(p_idx.size)
    Pc = P[torch.as_tensor(pi, device=dev)]
    kk = min(K + 1, pi.size)
    t0 = time.time()
    for a in range(0, qi.size, QCHUNK):
        rows = qi[a:a + QCHUNK]
        s = Q[torch.as_tensor(rows, device=dev)] @ Pc.T
        v, j = torch.topk(s, kk, dim=1)
        v, j = v.float().cpu().numpy(), pi[j.cpu().numpy()]
        for r, q in enumerate(rows):
            keep = p_idx[j[r]] != q_self[q]
            pv, vv = p_idx[j[r]][keep][:K], v[r][keep][:K]
            cols["qid"].append(np.full(pv.size, q_id[q], dtype=np.int64))
            cols["rank"].append(np.arange(1, pv.size + 1, dtype=np.int16))
            cols["pool_idx"].append(pv.astype(np.uint32))
            cols["cos"].append(vv.astype(np.float16))
    print(f"country {c!r}: {qi.size:,} queries x {pi.size:,} pool in {time.time() - t0:.0f}s", flush=True)

out = pa.table({k: pa.array(np.concatenate(v)) for k, v in cols.items()})
dst = Path("/tmp/retr_out") if not LOCAL else root
dst.mkdir(parents=True, exist_ok=True)
path = dst / f"{OUT_TAG}_topk.parquet"
pq.write_table(out, path, compression="zstd")
print(f"wrote {path}: {out.num_rows:,} rows; job {(time.time() - t_job) / 60:.1f} min", flush=True)
if not LOCAL:
    from huggingface_hub import HfApi
    HfApi().upload_file(path_or_fileobj=str(path), path_in_repo=f"retrieval/{OUT_TAG}_topk.parquet", repo_id=REPO,
                        repo_type="dataset", commit_message=f"retrieval {OUT_TAG}")
    print("uploaded", flush=True)
