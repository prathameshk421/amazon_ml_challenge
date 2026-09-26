# ce_rec_base on Kaggle: runbook

This runbook covers a full fine-tune of `BAAI/bge-reranker-base` (278M, MIT, sha `2cfc18c`) on DEV_REST_180K
pairs. The run scores MATCH_VALID, MATCH_TRAIN and TEST, and DEV_REST_REST only if the feature is adopted.
The scores become the `ce:ce_rec_base` feature group in `ber/exp.py`.

Plan: `~/.claude/plans/majestic-mapping-wren.md`. Background: `plan/TRANSFORMER_PLAN.md`.

- Quota: 30.00 GPU-h per week, resetting 2026-10-03 (`kaggle quota`, 2026-09-26).
- Account: `prathameshkinagi`. Auth: `~/.kaggle/access_token`, set up by the user.

## 0. Local prerequisites (once)

```bash
.venv/bin/python ce/prepare_pairs.py
```
This writes `work/ce/pairs_*.parquet` and `artifacts/metrics/ce_pairs_manifest.json`.

Download the checkpoint once (about 1.13 GB):
```bash
.venv/bin/python -c "from huggingface_hub import snapshot_download as s; s('BAAI/bge-reranker-base', revision='2cfc18c9415c912f9d8155881c133215df768a70', local_dir='work/ce/checkpoints/bge-reranker-base', allow_patterns=['config.json','model.safetensors','sentencepiece.bpe.model','special_tokens_map.json','tokenizer.json','tokenizer_config.json'])"
```

Stage the uploads under `work/ce/kaggle/`:
```bash
.venv/bin/python ce/kaggle/package.py --user prathameshkinagi
```

## 1. Upload the two private datasets

```bash
.venv/bin/kaggle datasets create -p work/ce/kaggle/pairs
```
```bash
.venv/bin/kaggle datasets create -p work/ce/kaggle/ckpt
```
After changing the scripts or pairs, push a new version:
```bash
.venv/bin/kaggle datasets version -p work/ce/kaggle/pairs -m "update"
```
Wait until `kaggle datasets status prathameshkinagi/ber-ce-pairs` reports `ready`.

## 2. Kernels (T4, internet off, private). Run one at a time.

| Kernel | Job | Expected time (c)+(d) | Output |
|---|---|---|---|
| `k0_probe` | 200 train steps plus 20k-pair scoring; extrapolated hours | ~15 min | `ce_rec_base/probe.json` |
| `k2_train_score` | smoke (stops if AUC does not improve), 1 epoch, then score MATCH_VALID/MATCH_TRAIN/TEST on both GPUs | ~1.5–4 h | `ce_rec_base/{model,train_meta.json,MATCH_*.parquet,TEST.parquet}`, `untrained_base/MATCH_VALID.parquet` |
| `k3_score_rest` | DEV_REST_REST, only if a `ce:ce_rec_base` M run is adopted | ~0.5–1 h | `ce_rec_base/DEV_REST_REST.parquet` |

```bash
.venv/bin/kaggle kernels push -p work/ce/kaggle/k0_probe
```
```bash
.venv/bin/kaggle kernels status prathameshkinagi/ber-ce-k0-probe
```
```bash
.venv/bin/kaggle kernels output prathameshkinagi/ber-ce-k0-probe -p work/ce/kaggle_out/k0
```

Read `probe.json` before pushing k2. If `hours_without_dev_rest_rest` is above ~10, stop and re-plan; see the
`rank <= 8` fallback in the plan. After k2 finishes, download its output and copy the score files into
`work/ce/ce_rec_base/` and `work/ce/untrained_base/`.

If the kernel ran on a P100 or a single GPU, the code still works, only more slowly. Check the `gpus` line at
the top of the kernel log.

If k2 hits the 12 h session limit, the chunks already written under `ce_rec_base/parts/` are lost, because
Kaggle only keeps output from finished versions. Re-plan with split kernels, one set per kernel.

## 3. Back on this machine

1. Run `.venv/bin/python ce/evaluate.py --ce ce_rec_base untrained_base` to write
   `artifacts/metrics/ce_rec_base_eval.json`.
2. Reload test: score 4 hand-written pairs with `work/ce/ce_rec_base/model` on CPU/MPS.
3. Matcher run: create `exps/M###.json` with `"groups": ["ce:ce_rec_base"]` and parent `x1_strsim`, then
   run `exp-train` and `exp-predict`. The rules are in `plan/EXPERIMENT_ROUTINE.md`, and the round cap per
   `plan/ROUND_CAP_EVIDENCE.md`.
4. Log every step in RESEARCH_LOG.md.
