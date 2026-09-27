"""Config B/C: set-transformer listwise matcher (BCE, 68 base features [+ p_ce/rank/gap]).

Trains on DEV_REST_180K candidate lists, scores MATCH_TRAIN (decision calibration)
and MATCH_VALID (paired comparison vs M027).

Usage (from amazon_ml_challenge/, with ber importable):
  python nn_listwise.py run                        # config B (68 feats)
  python nn_listwise.py run --extra ce --run NN_C  # config C (+p_ce/rank/gap)
  python nn_listwise.py predict --run NN_B --set MATCH_VALID   # score a set with a saved run

Outputs (AGENTS.md: every training run produces a submittable model):
  work/match/runs/<run>/models/{model.pt, norm.npz, matcher.json}
  work/match/runs/<run>/{TRAIN,VALID}_pairs.parquet, MATCH_VALID_per_entity.npy, queries.npy
  artifacts/metrics/nn_<run>_MATCH_VALID.json
"""

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "submission",
        "code",
        "business_entity_resolution",
        "src",
    ),
)
from ber import exp, io_utils, match  # noqa: E402

RUN = "NN_B"
TRAIN_SET = "DEV_REST_180K"
CAL_SET = "MATCH_TRAIN"
EVAL_SET = "MATCH_VALID"
VAL_S1 = 5000
SEED = 7

HP = dict(
    d_model=128,
    n_heads=4,
    n_sab=2,
    enc_hidden=256,
    dec_hidden=64,
    dropout=0.1,
    lr=3e-4,
    weight_decay=1e-2,
    batch_lists=1024,
    max_epochs=25,
    patience=5,
    pos_weight=8.0,
)


# ---------------------------------------------------------------- data


CE_DIR = "work/ce/ce_rec_c0"
EXTRA_COLS = {"ce": ["p_ce", "p_ce_rank", "p_ce_gap"]}


def load_lists(set_name, extra=None):
    X, s1, pool, meta = match.load_features(set_name)
    try:
        queries = match.set_queries(set_name)
    except (KeyError, ValueError):
        queries = np.unique(s1)
    y = match.pair_labels(s1, pool).astype(np.float32)
    extra_names = []
    if extra == "ce":
        import pandas as pd

        ce = pd.read_parquet(f"{CE_DIR}/{set_name}.parquet")
        df = pd.DataFrame({"s1_idx": s1, "pool_idx": pool.astype(np.int64)})
        m = df.merge(ce[["s1_idx", "pool_idx", "p_ce"]], on=["s1_idx", "pool_idx"], how="left")
        assert m["p_ce"].notna().all(), f"CE coverage gap on {set_name}"
        p = m["p_ce"].to_numpy(dtype=np.float32)
        rank = np.empty(len(p), dtype=np.float32)
        gap = np.empty(len(p), dtype=np.float32)
        uniq, start, stop = match.group_bounds(s1)  # rows are s1-sorted
        for a, b in zip(start.tolist(), stop.tolist()):
            blk = np.arange(a, b)
            o = blk[np.argsort(-p[blk], kind="stable")]
            rank[o] = np.arange(1, len(blk) + 1)
            gap[blk] = p[blk].max() - p[blk]
        X = np.column_stack([X, p, rank, gap]).astype(np.float32)
        extra_names = EXTRA_COLS["ce"]
    return X, s1, pool, y, queries, meta, extra_names


def fit_norm(X):
    """Column mean/std ignoring NaNs; NaN is mean-imputed (0 after standardize).

    Limitation vs LightGBM: M027 reads NaN-missingness natively (e.g. empty-address
    signals); here missingness collapses to the mean. Noted for the M041 writeup."""
    mu = np.nanmean(X, axis=0).astype(np.float32)
    sd = np.nanstd(X, axis=0).astype(np.float32) + 1e-6
    return mu, sd


def standardize(X, mu, sd):
    return np.nan_to_num((X - mu) / sd, nan=0.0, posinf=5.0, neginf=-5.0).astype(np.float32)


def split_train_val(queries, n_val, seed):
    rng = np.random.default_rng(seed)
    val_q = set(rng.choice(queries, size=min(n_val, len(queries)), replace=False).tolist())
    return np.array([q for q in queries if q not in val_q], dtype=np.int32), np.array(
        sorted(val_q), dtype=np.int32
    )


# ---------------------------------------------------------------- model


def build_model(hp, torch, in_dim):
    import torch.nn as nn

    class SAB(nn.Module):
        def __init__(self, d, heads, dropout):
            super().__init__()
            self.attn = nn.MultiheadAttention(d, heads, dropout=dropout, batch_first=True)
            self.n1 = nn.LayerNorm(d)
            self.ffn = nn.Sequential(
                nn.Linear(d, 2 * d), nn.GELU(), nn.Dropout(dropout), nn.Linear(2 * d, d)
            )
            self.n2 = nn.LayerNorm(d)
            self.drop = nn.Dropout(dropout)

        def forward(self, x, mask):
            h, _ = self.attn(self.n1(x), self.n1(x), self.n1(x), key_padding_mask=mask)
            x = x + self.drop(h)
            return x + self.drop(self.ffn(self.n2(x)))

    class SetMatcher(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = nn.Sequential(
                nn.Linear(in_dim, hp["enc_hidden"]),
                nn.LayerNorm(hp["enc_hidden"]),
                nn.GELU(),
                nn.Dropout(hp["dropout"]),
                nn.Linear(hp["enc_hidden"], hp["d_model"]),
                nn.LayerNorm(hp["d_model"]),
            )
            self.sabs = nn.ModuleList(
                [SAB(hp["d_model"], hp["n_heads"], hp["dropout"]) for _ in range(hp["n_sab"])]
            )
            self.dec = nn.Sequential(
                nn.LayerNorm(hp["d_model"]),
                nn.Linear(hp["d_model"], hp["dec_hidden"]),
                nn.GELU(),
                nn.Linear(hp["dec_hidden"], 1),
            )

        def forward(self, x, mask):
            h = self.enc(x)
            for sab in self.sabs:
                h = sab(h, mask)
            return self.dec(h).squeeze(-1)

    return SetMatcher()


def batch_lists(s1, order, batch, rng=None, chunk=4096):
    """Yield (rows, lengths) batches. `order` must sort s1 (row-permutation); shuffling
    happens at list level in chunks so batches stay length-homogeneous (less pad waste)."""
    _, start, stop = match.group_bounds(s1[order])
    ln = stop - start
    seq = np.argsort(-ln, kind="stable")
    if rng is not None:
        chunks = [seq[i : i + chunk] for i in range(0, len(seq), chunk)]
        rng.shuffle(chunks)
        seq = np.concatenate(chunks)
    for i in range(0, len(seq), batch):
        blk = seq[i : i + batch]
        mx = int(ln[blk].max())
        rows, lengths = [], []
        for j in blk:
            r = order[start[j] : stop[j]]
            lengths.append(len(r))
            if len(r) < mx:
                r = np.concatenate([r, np.full(mx - len(r), -1, dtype=np.int64)])
            rows.append(r)
        yield np.array(rows), np.array(lengths)


def train(hp, Xt, st, yt, Xv, sv, yv, qv, models_dir, lg=print):
    import torch
    import torch.nn as nn

    models_dir.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    lg(f"device: {dev}")
    mu, sd = fit_norm(Xt)
    Zt, Zv = standardize(Xt, mu, sd), standardize(Xv, mu, sd)
    model = build_model(hp, torch, Xt.shape[1]).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=hp["lr"], weight_decay=hp["weight_decay"])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=hp["max_epochs"])
    crit = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(hp["pos_weight"]), reduction="none")
    ot = np.argsort(st, kind="stable")
    ov = np.argsort(sv, kind="stable")

    def run_split(Z, s, y, order, train_mode, rng=None):
        tot_loss, tot_n = 0.0, 0
        lw = hp.get("listwise", 0.0)
        for rows, lengths in batch_lists(s, order, hp["batch_lists"], rng=rng):
            B, L = rows.shape
            xb = torch.from_numpy(Z[np.clip(rows, 0, len(Z) - 1)]).to(dev)
            yb = torch.from_numpy(y[np.clip(rows, 0, len(y) - 1)]).to(dev)
            keep = torch.from_numpy(rows >= 0).to(dev)
            logits = model(xb, ~keep)
            loss = (crit(logits, yb) * keep).sum() / keep.sum()
            if lw > 0:
                # ListNet top-1: softmax(logits) vs normalized label distribution,
                # mean over lists with >= 1 positive (handles multi-positive lists).
                lnet, n_l = 0.0, 0
                log_q = torch.log_softmax(logits.masked_fill(~keep, float("-inf")), dim=1)
                for i in range(B):
                    k = keep[i]
                    if yb[i][k].sum() > 0:
                        tgt = yb[i][k] / yb[i][k].sum()
                        lnet = lnet - (tgt * log_q[i][k]).sum()
                        n_l += 1
                if n_l:
                    loss = loss + lw * lnet / n_l
            if train_mode:
                opt.zero_grad()
                loss.backward()
                opt.step()
            tot_loss += float(loss.detach()) * int(keep.sum())
            tot_n += int(keep.sum())
        return tot_loss / tot_n

    scorer_v = match.Scorer(qv, sv, yv > 0.5, match.true_counts(qv))
    best, bad = np.inf, 0
    best_state = {k: v.cpu() for k, v in model.state_dict().items()}
    for ep in range(hp["max_epochs"]):
        model.train()
        tr = run_split(Zt, st, yt, ot, True, rng=np.random.default_rng(SEED + ep))
        model.eval()
        with torch.no_grad():
            va = run_split(Zv, sv, yv, ov, False)
        sched.step()
        # val entity F0.5 at fixed 0.5 for monitoring (decision is calibrated later)
        with torch.no_grad():
            pv = score_lists(model, Zv, sv, dev, hp["batch_lists"])
        f05v = scorer_v.f05(pv >= 0.5)
        tag = "loss" if hp.get("listwise", 0.0) > 0 else "bce"
        lg(
            f"epoch {ep + 1}: train_{tag}={tr:.4f} val_{tag}={va:.4f} val_f05@0.5={f05v:.5f}",
            flush=True,
        )
        if va < best - 1e-5:
            best, bad = va, 0
            best_state = {k: v.cpu() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= hp["patience"]:
                lg(f"early stop at epoch {ep + 1} (best val_bce={best:.4f})")
                break
    model.load_state_dict({k: v.to(dev) for k, v in best_state.items()})
    torch.save({"state_dict": best_state, "hp": hp, "seed": SEED}, models_dir / "model.pt")
    np.savez(models_dir / "norm.npz", mu=mu.astype(np.float32), sd=sd.astype(np.float32))
    return model, mu, sd


@np.errstate(all="ignore")
def score_lists(model, Z, s, dev, batch=2048):
    import torch

    model.eval()
    order = np.argsort(s, kind="stable")
    out = np.zeros(len(s), dtype=np.float32)
    with torch.no_grad():
        for rows, _ in batch_lists(s, order, batch):
            keep = rows >= 0
            xb = torch.from_numpy(Z[np.clip(rows, 0, len(Z) - 1)]).to(dev)
            mask = torch.from_numpy(~keep).to(dev)
            pr = torch.sigmoid(model(xb, mask)).cpu().numpy()
            out[np.array(rows)[keep]] = pr[keep]
    return out


# ---------------------------------------------------------------- run


def load_run_model(run, torch):
    rdir = match.runs_dir(run)
    mdir = rdir / "models"
    saved = torch.load(mdir / "model.pt", map_location="cpu", weights_only=False)
    norm = np.load(mdir / "norm.npz")
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(saved["hp"], torch, len(norm["mu"]))
    model.load_state_dict({k: v.to(dev) for k, v in saved["state_dict"].items()})
    model.to(dev)
    model.eval()
    return model, norm["mu"], norm["sd"], dev


def cmd_eval(args):
    import torch

    t0 = time.time()
    rdir = match.runs_dir(args.run)
    model, mu, sd, dev = load_run_model(args.run, torch)
    extra = args.extra
    if extra is None:
        mp = rdir / "models" / "matcher.json"
        if mp.exists():
            extra = io_utils.read_json(mp).get("extra")
    mcfg = match.load_match_config()
    import pandas as pd

    # calibrate decision on MATCH_TRAIN
    Xc, sc, poolc, _, _ = load_lists(CAL_SET, extra)[:5]
    yc = match.pair_labels(sc, poolc)
    qc = match.set_queries(CAL_SET)
    pc = score_lists(model, standardize(Xc, mu, sd), sc, dev)
    pd.DataFrame({"s1_idx": sc, "pool_idx": poolc, "p": pc}).to_parquet(
        rdir / f"{CAL_SET}_pairs.parquet"
    )
    decision, _, report, scores, sweep = exp.choose_decision(qc, sc, poolc, yc, pc, mcfg)
    lg = print
    lg(f"decision: {decision} f05={report['f05']:.5f}")

    # eval on MATCH_VALID, paired vs M027 (both scored in set_queries order)
    Xe, se, poole, _, _ = load_lists(EVAL_SET, extra)[:5]
    ye = match.pair_labels(se, poole)
    qe = match.set_queries(EVAL_SET)
    pe = score_lists(model, standardize(Xe, mu, sd), se, dev)
    pd.DataFrame({"s1_idx": se, "pool_idx": poole, "p": pe}).to_parquet(
        rdir / f"{EVAL_SET}_pairs.parquet"
    )
    keep = match.apply_decision(decision, se, poole, pe)
    scorer = match.Scorer(qe, se, ye, match.true_counts(qe))
    f_ent, _, _ = scorer.per_entity(keep)
    f05 = float(f_ent.mean())
    np.save(rdir / f"{EVAL_SET}_per_entity.npy", f_ent)
    np.save(rdir / "queries.npy", qe)
    fa = np.load(match.runs_dir("M027") / f"{EVAL_SET}_per_entity.npy")
    assert fa.shape == f_ent.shape == qe.shape, (fa.shape, f_ent.shape, qe.shape)
    cmp = match.paired_delta(f_ent, fa, n_boot=2000)
    lg(
        f"{EVAL_SET} F0.5: M027={fa.mean():.5f} NN={f05:.5f} paired Δ={cmp['delta']:+.5f} "
        f"[{cmp['ci95'][0]:+.5f}, {cmp['ci95'][1]:+.5f}] n_changed={cmp['n_changed']}"
    )

    meta = match.load_features(TRAIN_SET)[3]
    train_hp = torch.load(rdir / "models" / "model.pt", map_location="cpu", weights_only=False)[
        "hp"
    ]
    matcher = {
        "model_type": "set_transformer_bce",
        "run": args.run,
        "features": list(match.FEATURES),
        "extra": extra,
        "extra_cols": EXTRA_COLS.get(extra, []),
        "bucketing_fingerprint": meta["bucketing_fingerprint"],
        "train_set": TRAIN_SET,
        "hp": train_hp,
        "seed": SEED,
        "decision": decision,
        "cal_set": CAL_SET,
    }
    io_utils.atomic_write_json(rdir / "models" / "matcher.json", matcher)
    metrics = {
        "run": args.run,
        "train_set": TRAIN_SET,
        "eval_set": EVAL_SET,
        "f05_M027": float(fa.mean()),
        "f05_NN": f05,
        "paired_vs_M027": cmp,
        "decision": decision,
        "wall_min": (time.time() - t0) / 60,
    }
    mp = io_utils.write_metrics(
        f"nn_{args.run}_{EVAL_SET}", metrics, n_queries=len(qe), n_true_pairs=int(ye.sum())
    )
    lg(f"metrics -> {mp}  wall={(time.time() - t0) / 60:.1f} min")


def cmd_predict(args):
    import torch

    rdir = match.runs_dir(args.run)
    mdir = rdir / "models"
    saved = torch.load(mdir / "model.pt", map_location="cpu", weights_only=False)
    norm = np.load(mdir / "norm.npz")
    matcher = io_utils.read_json(mdir / "matcher.json")
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(saved["hp"], torch, len(norm["mu"]))
    model.load_state_dict({k: v.to(dev) for k, v in saved["state_dict"].items()})
    model.to(dev)
    model.eval()
    X, s, pool, _, _, meta, _ = load_lists(args.set, matcher.get("extra"))
    assert meta["bucketing_fingerprint"] == matcher["bucketing_fingerprint"], "fingerprint mismatch"
    Z = standardize(X, norm["mu"], norm["sd"])
    p = score_lists(model, Z, s, dev)
    import pandas as pd

    pd.DataFrame({"s1_idx": s, "pool_idx": pool, "p": p}).to_parquet(
        rdir / f"{args.set}_pairs.parquet"
    )
    keep = match.apply_decision(matcher["decision"], s, pool, p)
    print(
        f"{args.set}: {len(X)} rows, keep_rate={keep.mean():.4f} -> {rdir / f'{args.set}_pairs.parquet'}"
    )


def cmd_run(args):
    rdir = match.runs_dir(args.run)
    mdir = rdir / "models"
    mdir.mkdir(parents=True, exist_ok=True)
    lg = print

    X, s1, pool, y, queries, meta, extra_names = load_lists(TRAIN_SET, args.extra)
    assert list(meta["features"]) == list(match.FEATURES) and len(meta["features"]) == 68
    assert X.shape[1] == 68 + len(extra_names), (X.shape, extra_names)
    hp = dict(HP, listwise=args.listwise)
    lg(f"{TRAIN_SET}: {X.shape[0]} rows, {len(queries)} S1, pos_rate={y.mean():.4f}")
    tr_q, va_q = split_train_val(queries, VAL_S1, SEED)
    tr_m = np.isin(s1, tr_q)
    va_m = np.isin(s1, va_q)
    lg(f"train lists: {len(tr_q)} S1 / val lists: {len(va_q)} S1")
    train(hp, X[tr_m], s1[tr_m], y[tr_m], X[va_m], s1[va_m], y[va_m], va_q, mdir, lg=lg)
    cmd_eval(args)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--run", default=RUN)
    r.add_argument("--extra", default=None, choices=["ce"])
    r.add_argument("--listwise", type=float, default=0.0)
    e = sub.add_parser("eval")
    e.add_argument("--run", default=RUN)
    e.add_argument("--extra", default=None, choices=["ce"])
    p = sub.add_parser("predict")
    p.add_argument("--run", required=True)
    p.add_argument("--set", required=True)
    args = ap.parse_args()
    {"run": cmd_run, "eval": cmd_eval, "predict": cmd_predict}[args.cmd](args)


if __name__ == "__main__":
    main()
