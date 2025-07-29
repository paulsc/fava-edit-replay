"""Helpers for Beancount entries."""

from __future__ import annotations

from beancount.parser import parser
from beancount.core.number import MISSING
import re
import logging

from pathlib import Path
import json
from typing import Any
from fava.core.filters import AccountFilter, AdvancedFilter, TimeFilter
from fava.beans.abc import Transaction
from fava.core.file import get_entry_slice, find_entry_lines
from fava.beans.str import to_string
from fava.beans.funcs import get_position

from fava_edit_replay.replay import Replay

logger = logging.getLogger("edit_replay.helpers")
logger.setLevel(logging.INFO)


def txn_apply_delta(obj, delta):
    """
    Apply a DeepDiff Delta to a beancount transaction.

    Args:
        obj: The transaction to which the delta will be applied.
        delta: The object containing the changes, like:
               {
                 "values_changed": {
                   "root.payee": { "new_value": "Coffee Ship" },
                   "root.postings[0].units.number": { "new_value": "2.51" }
                 },
                 "set_item_added": { "root.tags": [ "yolo", "yili" ] },
                 "set_item_removed": { "root.tags": [ "tag1" ] },
                 "dictionary_item_added": { 
                   "root.meta['dkb_id']": "coolmeta" 
                 },
                 "dictionary_item_removed": {
                   "root.meta['note']": "yeah"
                 },
               }
 
    Returns:
        The modified transaction after applying the delta.

    Beancount transactions are NamedTuples, which can contain List[] or 
    fronzensets, or other NamedTuples, recursively. Since NamedTuples are 
    immutable, we use ._replace() to return a new NamedTuple with the desired 
    changes. We use a recursive algorithm:
      - start by splitting the diff path "root.postings[0].units.number" into 
        [ "root", "postings", 0, "number"]
      - if len(list) > 1: Do a recursive call, obj is now the first element 
        element in the list, accessed with getattr or [], and update the 
        current object with the result of the recursive call.
      - if len(list) = 1: We have arrived at the "leaf" of the tree, Update 
        the current obj according to the different cases.
    """

    def _apply_recursive(current_obj, path_parts, value, action):
        key = path_parts[0]
        remaining_path = path_parts[1:]

        if not remaining_path:  # Base case: last part of the path
            is_namedtuple = hasattr(current_obj, '_replace')
            if action == "dictionary_item_added" and isinstance(current_obj, dict):
                return {**current_obj, key: value}
            if action == "dictionary_item_removed" and isinstance(current_obj, dict):
                new_dict = current_obj.copy()
                del new_dict[key]
                return new_dict
            if is_namedtuple and action == "values_changed":
                return current_obj._replace(**{key: value})
            elif is_namedtuple and action == "set_item_added":
                newset = getattr(current_obj, key).union({value})
                return current_obj._replace(**{key: newset})
            elif is_namedtuple and action == "set_item_removed":
                newset = getattr(current_obj, key).difference({value})
                return current_obj._replace(**{key: newset})
            else:
                raise TypeError(f"Unsupported action/type")

        if isinstance(key, int):
            child_obj = current_obj[key]
        else:
            child_obj = getattr(current_obj, key)

        modified_child = _apply_recursive(child_obj, remaining_path, value, action)

        if isinstance(current_obj, list):
            new_list = current_obj[:]
            new_list[key] = modified_child
            return new_list
        elif hasattr(current_obj, '_replace'):
            return current_obj._replace(**{key: modified_child})
        else:
            raise TypeError(f"Unsuported object of type {type(current_obj)}.")

    def explode_path(path_str):
        """ 
        Split a path string into a list of path parts.
        explode_path('root.postings[0].units.number') -> ['postings', 0, 'number'] 
        """
        path_parts = [p for p in re.split(r'[.[\]\']+', path_str) if p]

        def try_int(s):
            try:
                return int(s)
            except ValueError:
                return s

        typed_path_parts = [try_int(p) for p in path_parts]

        if typed_path_parts and typed_path_parts[0] == 'root':
            typed_path_parts = typed_path_parts[1:]

        return typed_path_parts 

    def handle_single_delta(obj, path_str, change, action):
        typed_path_parts = explode_path(path_str)

        if isinstance(change, dict):
            return _apply_recursive(obj, typed_path_parts, change['new_value'], action) 
        elif isinstance(change, list):
            for item in change:
                 obj = _apply_recursive(obj, typed_path_parts, item, action)
            return obj
        elif isinstance(change, str):
            return _apply_recursive(obj, typed_path_parts, change, action) 
        else:
            raise TypeError("Invalid diff object")

    for action in delta.keys():
        for path, change_obj in delta[action].items():
            obj = handle_single_delta(obj, path, change_obj, action)

    return obj 


def make_filter_suggestions(slice_str: str) -> list[dict]:
    """
    Parse the transaction slice and return a list of dicts with keys:
    label (always), and only the relevant filter keys (date, account,
    filter), plus a tooltip string.
    """
    result = []
    if not slice_str:
        return result
    entries, errors, _ = parser.parse_string(slice_str)
    if errors or not entries:
        return result
    txn = entries[0]

    # Payee filter suggestion
    if txn.payee:
        result.append({ 'label': txn.payee, 'filter': f"payee: '{txn.payee}'" })

    # Narration filter suggestion
    if txn.narration:
        result.append({
            'label': txn.narration,
            'filter': f"narration: '{txn.narration}'"
        })

    # Date filter suggestion
    if txn.date:
        result.append({ 'label': txn.date, 'date': str(txn.date) })

    # Account filter and amount suggestion (from all postings)
    if hasattr(txn, 'postings') and txn.postings:
        for posting in txn.postings:
            acct = getattr(posting, 'account', None)
            if acct:
                result.append({ 'label': acct, 'account': acct })
            amount = getattr(posting, 'units', None)
            if amount and amount != MISSING:
                abs_int_amount = int(abs(amount.number))
                result.append({ 'label': amount, 'filter': f"={abs_int_amount}" })

    # Generate tooltip for each suggestion (excluding 'label')
    for d in result:
        tooltip = "\n".join(f"{v}" for k, v in d.items() if k != 'label')
        d['tooltip'] = tooltip

    return result


def transaction_matches_replay(txn, replay, options_map=None, fava_options=None):
    time_filter = replay.time_filter
    account_filter = replay.account_filter
    filter_string = replay.advanced_filter
    if not (account_filter or filter_string or time_filter):
        return False  # Don't allow global replays
    filters = []
    if time_filter and options_map and fava_options:
        filters.append(TimeFilter(options_map, fava_options, time_filter))
    if account_filter:
        filters.append(AccountFilter(account_filter))
    if filter_string:
        filters.append(AdvancedFilter(filter_string))
    for filter_obj in filters:
        entries = [txn]
        filtered_entries = filter_obj.apply(entries)
        if txn not in filtered_entries:
            return False
    return True


def apply_replays(
        replays: list[Replay], 
        entries: Any, 
        options_map: Any, 
        fava_options: Any, 
        verbose: bool = False
    ) -> int:
    """
    Apply a list of replays to a FavaLedger or FilteredLedger, modifying the in-memory
    lines of all relevant ledger files, and write all changes to disk at the end.
    Returns the number of modified transactions.
    """
    def log(msg: str):
        if verbose: print(msg)

    # Dict: { filename: [lines] }
    file_lines: dict[str, list[str]] = {}
    # Dict: { filename: set(line numbers that were changed) }
    file_changed: dict[str, set[int]] = {}
    modified_count = 0

    # Sort transactions in reverse line order for safe in-place editing
    txns = [e for e in entries if isinstance(e, Transaction)]
    txns.sort(key=lambda t: (get_position(t)[0], -get_position(t)[1]))

    for txn in txns:
        filename, lineno = get_position(txn)
        applied = False
        for replay in replays:
            diff_dict = json.loads(replay.diff)
            if transaction_matches_replay(txn, replay, options_map, fava_options):
                original_slice, _ = get_entry_slice(txn)
                parsed_entries, errors, _ = parser.parse_string(original_slice)
                if errors or not parsed_entries:
                    break
                parsed_txn = parsed_entries[0]
                modified_txn = txn_apply_delta(parsed_txn, diff_dict)
                applied = True
                break  # Only apply the first matching replay for this txn
        if applied:
            if filename not in file_lines:
                with open(filename, 'r', encoding='utf-8') as f:
                    file_lines[filename] = f.readlines()
                file_changed[filename] = set()
            currency_column = fava_options.currency_column
            indent = fava_options.indent
            modified_slice = to_string(modified_txn, currency_column, indent).rstrip()
            lines = file_lines[filename]
            entry_lines = find_entry_lines(lines, lineno - 1)
            entry_len = len(entry_lines)
            original_slice, _ = get_entry_slice(txn)
            if original_slice != modified_slice:
                # Logging: Match: {lineno} [{first_line_capped}]
                first_line_capped = original_slice.splitlines()[0][:70].ljust(70)
                log(f"Match: #{str(lineno).ljust(6)} [{first_line_capped}]")
                file_lines[filename] = (
                    lines[:lineno - 1]
                    + [modified_slice + '\n']
                    + lines[lineno - 1 + entry_len:]
                )
                file_changed[filename].add(lineno)
                modified_count += 1

    # Write all changed files
    for filename, changed_lines in file_changed.items():
        if changed_lines:
            with open(filename, 'w', encoding='utf-8') as f:
                f.writelines(file_lines[filename])
            # Logging: Wrote file: {filename}
            log(f"Wrote file: {filename}")
    return modified_count