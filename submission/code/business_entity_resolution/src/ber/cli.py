"""Command-line entry point (plan §7): `python -m ber.cli <command> [args]` from the repository root."""

import argparse
import importlib

SPLITS = ("train", "test")

# command -> (module, function)
COMMANDS = {
    "ingest": ("ingest", "run_ingest"),
    "splits": ("splits", "run_splits"),
    "mine-abbrev": ("abbrev_mine", "run_mine_abbrev"),
    "abbrev-e0": ("abbrev_mine", "run_abbrev_e0"),
    "normalize": ("textnorm", "run_normalize"),
    "learn-dict": ("translit_dict", "run_learn_dict"),
    "build-index": ("index_build", "run_build_index"),
    "index-sanity": ("index_build", "run_index_sanity"),
    "s1-eval": ("evaluate", "run_s1_eval"),
    "stage1-train": ("stage1_model", "run_stage1_train"),
    "rerank-build": ("rerank", "run_rerank_build"),
    "rerank-train": ("rerank", "run_rerank_train"),
    "rerank-cut": ("rerank", "run_rerank_cut"),
    "rerank-loco": ("rerank", "run_rerank_loco"),
    "rerank-eval": ("rerank", "run_rerank_eval"),
    "candidates": ("run_candidates", "run_candidates"),
    "write-outputs": ("write_outputs", "run_write_outputs"),
    "monitor": ("monitor", "run_monitor"),
}


def build_parser():
    p = argparse.ArgumentParser(prog="ber")
    sub = p.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        sub.add_parser(name)
    parsers = sub.choices

    for name in ("ingest", "mine-abbrev", "build-index", "index-sanity"):
        parsers[name].add_argument("--split", choices=SPLITS, required=True)

    n = parsers["normalize"]
    n.add_argument("--split", choices=SPLITS, required=True)
    n.add_argument("--no-dict", action="store_true")
    n.add_argument("--no-abbrev", action="store_true")

    s = parsers["s1-eval"]
    s.add_argument("--set", default="DEV_A")
    s.add_argument("--exp", required=True)
    s.add_argument("--families", nargs="+")
    s.add_argument("--cap", nargs="+", default=[], metavar="F=x")
    s.add_argument("--quota-grid", action="store_true")
    s.add_argument("--scorer", choices=("hand", "learn"), default="hand")

    parsers["rerank-eval"].add_argument("--set", choices=("DEV_B", "HOLDOUT_TEST"), required=True)

    c = parsers["candidates"]
    c.add_argument("--set", choices=("MATCH_TRAIN", "MATCH_VALID", "HOLDOUT_TEST", "TEST"),
                   required=True)
    c.add_argument("--limit", type=int)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    module, func = COMMANDS[args.command]
    getattr(importlib.import_module(f"ber.{module}"), func)(args)


if __name__ == "__main__":
    main()
