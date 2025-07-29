#!/usr/bin/env python3
import sys
import os
from pathlib import Path
from beancount import loader
from beancount.core.data import Custom

from fava_edit_replay.helpers import apply_replays
from fava_edit_replay.replay import load_replays_from_file

from fava.core.fava_options import parse_options

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Apply all replays from a yaml file to a Beancount ledger file.")
    parser.add_argument('replays_file', help='Path to the replays.yaml file')
    parser.add_argument('ledger_file', help='Path to the Beancount ledger file')
    args = parser.parse_args()
    replay_yaml = Path(args.replays_file)
    replays = load_replays_from_file(replay_yaml)
    entries, errors, options_map = loader.load_file(args.ledger_file)
    if errors:
        print(f"WARNING: Errors parsing ledger: {errors}")
    custom_entries = [e for e in entries if type(e) == Custom]
    fava_options, fava_options_errors = parse_options(custom_entries)
    if fava_options_errors:
        print(f"WARNING: Errors parsing fava options: {fava_options_errors}")
    apply_replays(replays, entries, options_map, fava_options, verbose=True)

if __name__ == "__main__":
    main() 