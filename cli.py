#!/usr/bin/env python3
import sys
import os
import yaml
from pathlib import Path
from beancount import loader
from beancount.core.data import Custom

# add the parent dir to the path so that we can import the helpers
# there has to be a better way to do this
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers import apply_replays
from replay import load_replays_from_file

# Add FAVA source to path for importing filtering code
sys.path.append(os.path.expanduser('~/Workspace/fava/src'))
from fava.core.filters import AdvancedFilter, AccountFilter, TimeFilter
from fava.core.fava_options import parse_options

def create_fava_filters(time_filter, account_filter, filter_string, options_map=None, fava_options=None):
    filters = []
    if time_filter and options_map and fava_options:
        filters.append(TimeFilter(options_map, fava_options, time_filter))
    if account_filter:
        filters.append(AccountFilter(account_filter))
    if filter_string:
        filters.append(AdvancedFilter(filter_string))
    return filters

def transaction_matches_replay(txn, replay, options_map=None, fava_options=None):
    time_filter = replay.get('time')
    account_filter = replay.get('account')
    filter_string = replay.get('filter')
    if not (account_filter or filter_string or time_filter):
        return False  # Don't allow global replays
    filters = create_fava_filters(time_filter, account_filter, filter_string, options_map, fava_options)
    for filter_obj in filters:
        entries = [txn]
        filtered_entries = filter_obj.apply(entries)
        if txn not in filtered_entries:
            return False
    return True

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