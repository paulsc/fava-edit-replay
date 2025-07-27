"""Bulk edit extension for Fava.
"""

from __future__ import annotations

import datetime
import json
from decimal import Decimal
from functools import partial
from pathlib import Path

from beancount.core.data import Transaction
from beancount.parser import parser
from deepdiff import DeepDiff
from deepdiff import Delta
from deepdiff.serialization import json_dumps
from flask import request

import yaml
from yaml.loader import SafeLoader

from fava.beans.str import to_string
from fava.context import g
from fava.core.file import get_entry_slice
from fava.ext import FavaExtensionBase
from fava.ext import extension_endpoint

from fava_edit_replay.helpers import apply_replays, make_filter_suggestions
from fava_edit_replay.diff2text import format_diff
from fava_edit_replay.replay import Replay, save_replay_to_file, load_replays_from_file

import logging
logger = logging.getLogger("edit_replay")
logger.setLevel(logging.DEBUG)

class EditReplay(FavaExtensionBase):  # pragma: no cover
    """Bulk edit extension for Fava."""

    report_title = "Edit Replay"
    has_js_module = True

    before_slice: str | None = None
    after_slice: str | None = None

    def database_path(self):
        return self.ledger.join_path(self.config.get("db", "replays.yaml"))

    def get_transactions(self, ledger):
        return [
            entry for entry in ledger.entries
            if isinstance(entry, Transaction) and entry.flag != 'S'
        ]

    @extension_endpoint
    def apply_diff(self):
        """Apply a diff to all filtered transactions."""
        # Get diff from query string parameter
        diff_json = request.args.get("diff", "")
        if not diff_json:
            logger.error("No diff provided.")
            return "No diff provided."

        # Get filter params from request
        account = request.args.get("account", "")
        filter_str = request.args.get("filter", "")
        time = request.args.get("time", "")

        # Validate that at least one filter is provided to prevent bulk changes
        if not account and not filter_str and not time:
            return (
                "At least one filter (account, filter, or time) must be specified "
                "to prevent bulk changes to all transactions."
            )

        filtered_ledger = self.ledger.get_filtered(
            account=account,
            filter=filter_str,
            time=time,
        )

        replay = Replay(0, time, account, filter_str, diff_json, None)
        modified_count = apply_replays(
            [replay], 
            filtered_ledger.entries, 
            filtered_ledger.ledger.options,
            self.ledger.fava_options
        )
        self.ledger.load_file()
        return f"Applied diff to {modified_count} transactions."

    @extension_endpoint
    def save_replay(self):
        """Save the current diff and filters as a replay to a YAML file."""
        replay = Replay(
            lineno=-1,
            time_filter=request.args.get("time", ""),
            account_filter=request.args.get("account", ""),
            advanced_filter=request.args.get("filter", ""),
            diff=request.args.get("diff", ""),
            diff_readable=None,
        )
        save_replay_to_file(replay, self.database_path())
        return "Replay saved."

    def before_request(self):
        if request.path.endswith("/api/source_slice") and request.method == "PUT":
            data = request.get_json(force=True, silent=True)
            if data:
                entry_hash = data.get("entry_hash")
                new_source = data.get("source")
                if entry_hash and new_source:
                    try:
                        entry = self.ledger.get_entry(entry_hash)
                        if not isinstance(entry, Transaction):
                            return
                        before, _ = get_entry_slice(entry)
                    except Exception as e:
                        before = f"[Error getting before slice: {e}]"
                    after = new_source
                    self.before_slice = before
                    self.after_slice = after

    def _compute_diff(self, before: str, after: str) -> str | None:
        """Computes the semantic diff between two transaction source strings."""
        if not before or not after:
            logger.error("No transaction diff available: before or after is empty.")
            return None
        try:
            original_entries, o_errors, _ = parser.parse_string(before)
            modified_entries, m_errors, _ = parser.parse_string(after)
            if o_errors or m_errors:
                logger.error(f"Parse error: {o_errors} {m_errors}")
                return None
            if not original_entries or not modified_entries:
                logger.error("Invalid transaction slices provided.")
                return None
            diff = DeepDiff(
                original_entries[0],
                modified_entries[0],
            )
            custom_json_dumps = partial(
                json_dumps, default_mapping={datetime.date: str, Decimal: str}
            )
            delta = Delta(diff, serializer=custom_json_dumps)
            self._remove_lineno_changed(delta.diff)
            return delta.dumps()
        except Exception as e:
            logger.error(f"Error computing diff: {e}")
            return None

    def _remove_lineno_changed(self, diff_dict):
        """
        Remove line diffs like below, they happen when inserting meta for
        example, which ends up changing the line number of the posting.
          "values_changed": {
              "root.postings[0].meta['lineno']": { "new_value": "2.51" }
          },
        """
        for key, value in diff_dict.items():
            if key == "values_changed":
                # Collect keys to delete first
                keys_to_delete = [k for k in value if "lineno" in k]
                for k in keys_to_delete:
                    del diff_dict[key][k]
        return diff_dict

    def get_data(self):
        txns = self.get_transactions(g.filtered)
        lastdiff_readable = []
        lastdiff_json = None
        filter_suggestions = []

        # Check for diff in query string parameters first
        diff_from_query = request.args.get("diff", "")
        if diff_from_query:
            lastdiff_json = diff_from_query
            diff_dict = json.loads(diff_from_query)
            lastdiff_readable = format_diff(diff_dict)
        elif self.before_slice is not None and self.after_slice is not None:
            lastdiff_json = self._compute_diff(self.before_slice, self.after_slice)
            if lastdiff_json:
                diff_dict = json.loads(lastdiff_json)
                lastdiff_readable = format_diff(diff_dict)
            filter_suggestions = make_filter_suggestions(self.before_slice)

        replays = load_replays_from_file(self.database_path())
        return {
            "transactions": txns,
            "lastdiff_readable": lastdiff_readable,
            "lastdiff_json": lastdiff_json,
            "filter_suggestions": filter_suggestions,
            "replays": replays,
        }


