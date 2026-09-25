"""Splits and query sets (plan §5.4): train S1 -> dev / HOLDOUT_TEST and the dev query sets."""

import json
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from ber import io_utils

SPLIT_SEED = 42
PERM_SEED = 20260925
HOLDOUT_SIZE = 441_365  # ceil(0.2 * 2,206,821), plan §5.4 step 2
# (name, start, stop) slices of the dev permutation; stop None = to the end
PERM_SLICES = [("DEV_A", 0, 10_000), ("DEV_B", 10_000, 20_000), ("S1R_TRAIN", 20_000, 40_000),
               ("RR_TRAIN", 40_000, 90_000), ("RR_CAL", 90_000, 110_000),
               ("MATCH_TRAIN", 110_000, 290_000), ("MATCH_VALID", 290_000, 310_000),
               ("DEV_REST", 310_000, None)]
DISJOINT_SETS = [name for name, _, _ in PERM_SLICES] + ["HOLDOUT_TEST"]


def _query_sets_path():
    return io_utils.work_path("splits", "query_sets.json")


def build_sets(entity_id, country, nmatch):
    """entity_id / country (str) / nmatch aligned by s1_idx -> {SET: sorted s1_idx int32 array}."""
    s1 = pd.DataFrame({"entity_id": entity_id, "country": country,
                       "mbin": np.minimum(nmatch, 6)})
    s1_idx = pd.Series(np.arange(len(s1), dtype=np.int32), index=s1["entity_id"])
    s1 = s1.sort_values("entity_id", kind="stable")
    ids = s1["entity_id"].tolist()
    strata = (s1["country"] + "|" + s1["mbin"].astype(str)).tolist()
    dev, holdout = train_test_split(ids, test_size=0.2, stratify=strata, random_state=SPLIT_SEED)
    if len(holdout) != HOLDOUT_SIZE:
        raise ValueError(f"HOLDOUT_TEST has {len(holdout)} entities, expected {HOLDOUT_SIZE}")
    perm = np.random.default_rng(PERM_SEED).permutation(sorted(dev))
    named = {name: perm[a:b] for name, a, b in PERM_SLICES}
    named["HOLDOUT_TEST"] = holdout
    ab = set(named["DEV_A"]) | set(named["DEV_B"])
    named["DICT_SRC"] = [e for e in dev if e not in ab]
    sets = {name: np.sort(s1_idx.loc[list(v)].to_numpy(np.int32)) for name, v in named.items()}
    allidx = np.concatenate([sets[n] for n in DISJOINT_SETS])
    if allidx.size != len(s1) or np.unique(allidx).size != len(s1):
        raise ValueError("query sets are not pairwise disjoint or do not cover all train S1")
    return sets


def _distribution(values):
    return {str(k): int(v) for k, v in sorted(Counter(values.tolist()).items())}


def run_splits(args):
    """CLI `splits` (plan §5.4, §7)."""
    log = io_utils.get_logger("splits")
    s1 = pd.read_parquet(io_utils.work_path("records", "train_s1.parquet"),
                         columns=["s1_idx", "entity_id", "country_raw"])
    if not np.array_equal(s1["s1_idx"].to_numpy(), np.arange(len(s1))):
        raise ValueError("train_s1.parquet s1_idx is not 0..n-1 in order")
    nmatch = np.load(io_utils.work_path("records", "train_s1_nmatch.npy"))
    sets = build_sets(s1["entity_id"].to_numpy(), s1["country_raw"].to_numpy(), nmatch)
    sizes = {name: int(v.size) for name, v in sets.items()}
    seeds = {"train_test_split_random_state": SPLIT_SEED, "permutation_seed": PERM_SEED}
    doc = {"sets": {name: v.tolist() for name, v in sets.items()}, "sizes": sizes, "seeds": seeds}
    path = _query_sets_path()
    io_utils.atomic_write_text(path, json.dumps(doc, separators=(",", ":")) + "\n")
    country = s1["country_raw"].to_numpy()
    per_set = {name: {"n": sizes[name], "country": _distribution(country[v]),
                      "nmatch": _distribution(nmatch[v])} for name, v in sets.items()}
    io_utils.write_metrics("splits", {"sizes": sizes, "seeds": seeds, "per_set": per_set},
                           n_queries=len(s1), n_true_pairs=int(nmatch.sum()))
    log.info("splits written: %s %s", path, sizes)


def load_query_sets():
    """{SET: sorted s1_idx int32 array} from splits/query_sets.json."""
    doc = io_utils.read_json(_query_sets_path())
    return {name: np.asarray(v, dtype=np.int32) for name, v in doc["sets"].items()}
