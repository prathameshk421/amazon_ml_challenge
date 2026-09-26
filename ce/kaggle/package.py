"""Stage the Kaggle uploads under work/ce/kaggle/ (no network; the `kaggle` CLI commands in README.md upload).

  .venv/bin/python ce/kaggle/package.py --user <kaggle username> 

work/ce/kaggle/
  pairs/        pairs_*.parquet (hard links, no copy) + ce/{common,train,inference,probe}.py + dataset-metadata.json
  k0_probe/, k2_train_score/, k3_score_rest/   kaggle_run.py with JOB filled in + kernel-metadata.json
All datasets and kernels are private; kernels run on T4. k0/k2 have internet on only to download the pinned
checkpoint from the Hugging Face hub; k3 (scoring with the k2 model) runs with internet off.
"""
import argparse
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "work" / "ce" / "kaggle"
PAIR_SETS = ("DEV_REST_180K", "MATCH_TRAIN", "MATCH_VALID", "TEST", "DEV_REST_REST")
SCRIPTS = ("common.py", "train.py", "inference.py", "probe.py")
KERNELS = {"k0_probe": "probe", "k2_train_score": "train_score", "k3_score_rest": "score_rest"}


def link(src, dst):
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def write(path, doc):
    path.write_text(json.dumps(doc, indent=1) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    args = ap.parse_args()
    u = args.user

    d = STAGE / "pairs"
    d.mkdir(parents=True, exist_ok=True)
    for s in PAIR_SETS:
        link(ROOT / "work" / "ce" / f"pairs_{s}.parquet", d / f"pairs_{s}.parquet")
    for f in SCRIPTS:
        shutil.copy2(ROOT / "ce" / f, d / f)
    write(d / "dataset-metadata.json", {"title": "ber-ce-pairs", "id": f"{u}/ber-ce-pairs",
                                        "licenses": [{"name": "other"}], "isPrivate": True})

    for folder, job in KERNELS.items():
        k = STAGE / folder
        k.mkdir(parents=True, exist_ok=True)
        code = (ROOT / "ce" / "kaggle" / "kaggle_run.py").read_text().replace('"__JOB__"', f'"{job}"')
        (k / "kaggle_run.py").write_text(code)
        meta = {"id": f"{u}/ber-ce-{folder.replace('_', '-')}", "title": f"ber-ce-{folder.replace('_', '-')}",
                "code_file": "kaggle_run.py", "language": "python", "kernel_type": "script", "is_private": True,
                "enable_gpu": True, "enable_internet": job != "score_rest", "machine_shape": "NvidiaTeslaT4",
                "dataset_sources": [f"{u}/ber-ce-pairs"],
                "kernel_sources": [f"{u}/ber-ce-k2-train-score"] if job == "score_rest" else [],
                "competition_sources": []}
        write(k / "kernel-metadata.json", meta)
    print("staged", STAGE)
    for p in sorted(STAGE.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(STAGE)}  {p.stat().st_size / 2**20:.1f} MB")


if __name__ == "__main__":
    main()
