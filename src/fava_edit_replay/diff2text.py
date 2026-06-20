from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from beancount.core.number import MISSING

DiffKind = Literal["normal", "changed", "removed", "added"]


@dataclass
class DiffSpan:
    text: str
    kind: DiffKind


@dataclass
class TxnDiffDisplay:
    lines: list[list[DiffSpan]]


@dataclass
class DiffIndex:
    fields: dict[str, tuple[DiffKind, Any]]
    tags_removed: set[str]
    tags_added: set[str]


def format_diff(delta):
    """
    Format a DeepDiff delta as a list of readable English text lines.
    Args:
        delta: The delta object containing the changes
    Returns:
        A list of strings, each describing a change
        
    Date, Flag, Payee and Narration edits show up as "values_changed":
    {
      "values_changed": {
        "root.date": { "new_value": "2021-01-01" },
        "root.flag": { "new_value": "*" },
        "root.narration": { "new_value": "Sal feb" }
      }
    }
    
    Posting account and amount changes also show up as "values_changed":
    {
      "values_changed": {
        "root.postings[0].units.number": { "new_value": "1200.00" },
        "root.postings[1].account": { "new_value": "Income:Misc" }
      }
    }
    
    Adding or removing a Payee (i.e. going from Narration only to Payee + 
    Narration) shows up as "type_changes" going to/from NoneType. E.g:
    {
      "type_changes": {
        "root.payee": {
          "old_type": "NoneType",
          "new_type": "str",
          "new_value": "Hooli"
        }
      }
    }
    
    Editing tags is set_item_removed and set_item_added:
    {
      "set_item_removed": { "root.tags": [ "cooltag1" ] },
      "set_item_added": { "root.tags": [ "tag2" ] }
    }
    
    Editing meta is dictionary_item_added and _removed:
    {
      "dictionary_item_added": { "root.meta['note']": "cool meta" },
    }
    
    """
    if not delta:
        return ["No changes"]

    changes = []

    # Handle values_changed
    if "values_changed" in delta:
        for path, change in delta["values_changed"].items():
            field_name = _format_field_name(path)
            new_value = change.get("new_value", "")
            changes.append(f'{field_name} changed to "{new_value}"')

    # Handle type_changes
    if "type_changes" in delta:
        for path, change in delta["type_changes"].items():
            field_name = _format_field_name(path)
            new_value = change.get("new_value", "")
            old_type = change.get("old_type", "")
            new_type = change.get("new_type", "")

            if new_type == "NoneType":
                changes.append(f'{field_name} removed.')
            elif old_type == "NoneType":
                changes.append(f'{field_name} set to "{new_value}"')
            else:
                changes.append(f'{field_name} changed from {old_type} to {new_type} ("{new_value}")')

    # Handle set_item_added
    if "set_item_added" in delta:
        for path, items in delta["set_item_added"].items():
            if isinstance(items, list):
                for item in items:
                    changes.append(f'Added to {_format_field_name(path)}: "{item}"')
            else:
                changes.append(f'Added to {_format_field_name(path)}: "{items}"')

    # Handle set_item_removed
    if "set_item_removed" in delta:
        for path, items in delta["set_item_removed"].items():
            if isinstance(items, list):
                for item in items:
                    changes.append(f'Removed from {_format_field_name(path)}: "{item}"')
            else:
                changes.append(f'Removed from {_format_field_name(path)}: "{items}"')

    # Handle dictionary_item_added
    if "dictionary_item_added" in delta:
        for path, value in delta["dictionary_item_added"].items():
            if "meta" in path:
                meta_key = _extract_meta_key(path)
                changes.append(f'Added metadata: "{meta_key}: {value}"')
            else: 
                # is this needed below? Do we only have meta as dict or are
                # there other dicts?
                changes.append(f'Added {_format_field_name(path)}: "{value}"')

    # Handle dictionary_item_removed
    if "dictionary_item_removed" in delta:
        for path, value in delta["dictionary_item_removed"].items():
            if "meta" in path:
                meta_key = _extract_meta_key(path)
                changes.append(f'Removed metadata: "{meta_key}"')
            else:
                changes.append(f'Removed {_format_field_name(path)}: "{value}"')

    return changes if changes else ["No changes"]

def _format_field_name(path):
    """
    Convert a path like 'root.postings[0].units.number' to readable text.
    """
    # Remove 'root.' prefix
    if path.startswith('root.'):
        path = path[5:]

    # Handle postings with indices
    posting_match = re.match(r'postings\[(\d+)\]', path)
    if posting_match:
        index = int(posting_match.group(1))
        if index == 0:
            posting_text = "First posting"
        elif index == 1:
            posting_text = "Second posting"
        elif index == 2:
            posting_text = "Third posting"
        else:
            posting_text = f"{index + 1}th posting"

        # Replace the posting part and continue with the rest
        remaining = path[posting_match.end():]
        if remaining.startswith('.'):
            remaining = remaining[1:]

        if remaining == 'units.number':
            return f"{posting_text} amount"
        elif remaining:
            return f"{posting_text} {remaining.replace('_', ' ').title()}"
        else:
            return posting_text

    # Split by dots and format each part
    parts = path.split('.')
    formatted_parts = []

    for part in parts:
        # Convert snake_case to Title Case
        formatted_parts.append(part.replace('_', ' ').title())

    return ' '.join(formatted_parts)

def _extract_meta_key(path):
    """
    Extract the metadata key from a path like 'root.meta["dkb_id"]'
    """
    # Look for the pattern meta['key'] or meta["key"]
    match = re.search(r'meta\[[\'"]([^\'"]+)[\'"]\]', path)
    if match:
        return match.group(1)
    return "unknown"


def build_diff_index(diff_dict: dict) -> DiffIndex:
    """Normalize DeepDiff paths into a lookup for ledger diff rendering."""
    fields: dict[str, tuple[DiffKind, Any]] = {}
    tags_removed: set[str] = set()
    tags_added: set[str] = set()

    if not diff_dict:
        return DiffIndex(fields, tags_removed, tags_added)

    for path, change in diff_dict.get("values_changed", {}).items():
        fields[path] = ("changed", change.get("new_value"))

    for path, change in diff_dict.get("type_changes", {}).items():
        new_type = change.get("new_type", "")
        old_type = change.get("old_type", "")
        if new_type == "NoneType":
            fields[path] = ("removed", None)
        elif old_type == "NoneType":
            fields[path] = ("added", change.get("new_value"))
        else:
            fields[path] = ("changed", change.get("new_value"))

    for path, items in diff_dict.get("set_item_removed", {}).items():
        if path == "root.tags":
            tag_list = items if isinstance(items, list) else [items]
            tags_removed.update(tag_list)
        else:
            for item in (items if isinstance(items, list) else [items]):
                fields[path] = ("removed", item)

    for path, items in diff_dict.get("set_item_added", {}).items():
        if path == "root.tags":
            tag_list = items if isinstance(items, list) else [items]
            tags_added.update(tag_list)
        else:
            for item in (items if isinstance(items, list) else [items]):
                fields[path] = ("added", item)

    for path, value in diff_dict.get("dictionary_item_added", {}).items():
        fields[path] = ("added", value)

    for path, value in diff_dict.get("dictionary_item_removed", {}).items():
        fields[path] = ("removed", value)

    return DiffIndex(fields, tags_removed, tags_added)


def build_txn_diff_display(before_txn, after_txn, diff_dict: dict) -> TxnDiffDisplay | None:
    """Build a ledger-format diff display from parsed transactions and a diff."""
    if not before_txn or not diff_dict:
        return None

    index = build_diff_index(diff_dict)
    after_txn = after_txn or before_txn

    header_spans: list[DiffSpan] = []
    header_spans.extend(_header_date_flag_spans(before_txn, after_txn, index))
    header_spans.extend(_header_quoted_field(
        "root.payee", before_txn.payee, after_txn.payee, index, suffix_space=True
    ))
    header_spans.extend(_header_quoted_field(
        "root.narration", before_txn.narration, after_txn.narration, index
    ))
    header_spans.extend(_header_tag_spans(before_txn, index))

    meta_lines = _meta_line_spans(before_txn, after_txn, index)
    posting_lines = _posting_line_spans(before_txn, after_txn, index)

    lines: list[list[DiffSpan]] = [header_spans]
    lines.extend(meta_lines)
    for account_spans, amount_spans in posting_lines:
        lines.append(account_spans + amount_spans)

    return TxnDiffDisplay(lines)


def _quote_if_needed(value: str) -> str:
    if not value:
        return value
    if any(c in value for c in ' \t:#"'):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _quote_always(value: str) -> str:
    if not value:
        return value
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def _format_meta_value(value: Any) -> str:
    if isinstance(value, str):
        return _quote_if_needed(value)
    return str(value)


def _format_amount(posting) -> str:
    units = getattr(posting, "units", None)
    if not units or units is MISSING or not hasattr(units, "number"):
        return ""
    return f"{units.number} {units.currency}"


def _span_for_field(
    path: str,
    before_value: Any,
    after_value: Any,
    index: DiffIndex,
    formatter=None,
) -> DiffSpan:
    formatter = formatter or str
    entry = index.fields.get(path)
    if entry:
        kind, diff_value = entry
        if kind == "removed":
            return DiffSpan(formatter(before_value), "removed")
        if kind in ("changed", "added"):
            display = after_value if after_value is not None else diff_value
            return DiffSpan(formatter(display), kind)
    return DiffSpan(formatter(before_value), "normal")


def _header_quoted_field(
    path: str,
    before: str | None,
    after: str | None,
    index: DiffIndex,
    suffix_space: bool = False,
) -> list[DiffSpan]:
    if not before and not after and path not in index.fields:
        return []
    spans = [_span_for_field(path, before or "", after or "", index, _quote_always)]
    if suffix_space:
        spans.append(DiffSpan(" ", "normal"))
    return spans


def _header_date_flag_spans(before_txn, after_txn, index: DiffIndex) -> list[DiffSpan]:
    spans = [
        _span_for_field("root.date", before_txn.date, after_txn.date, index),
        DiffSpan(" ", "normal"),
        _span_for_field("root.flag", before_txn.flag or "*", after_txn.flag or "*", index),
        DiffSpan(" ", "normal"),
    ]
    return spans


def _header_tag_spans(before_txn, index: DiffIndex) -> list[DiffSpan]:
    spans: list[DiffSpan] = []
    for tag in sorted(before_txn.tags):
        spans.append(DiffSpan(" ", "normal"))
        if tag in index.tags_removed:
            spans.append(DiffSpan(f"#{tag}", "removed"))
        else:
            spans.append(DiffSpan(f"#{tag}", "normal"))
    for tag in sorted(index.tags_added):
        if tag not in before_txn.tags:
            spans.append(DiffSpan(" ", "normal"))
            spans.append(DiffSpan(f"#{tag}", "added"))
    return spans


def _meta_path(key: str) -> str:
    return f"root.meta['{key}']"


def _meta_line_spans(before_txn, after_txn, index: DiffIndex) -> list[list[DiffSpan]]:
    before_meta = {
        k: v for k, v in (before_txn.meta or {}).items()
        if k not in ("lineno", "filename")
    }
    after_meta = {
        k: v for k, v in (after_txn.meta or {}).items()
        if k not in ("lineno", "filename")
    }
    keys: list[str] = []
    for key in before_meta:
        if key not in keys:
            keys.append(key)
    for key in after_meta:
        if key not in keys:
            keys.append(key)

    lines: list[list[DiffSpan]] = []
    for key in keys:
        path = _meta_path(key)
        before_value = before_meta.get(key)
        after_value = after_meta.get(key)
        entry = index.fields.get(path)

        if entry:
            kind, diff_value = entry
            if kind == "removed" and before_value is not None:
                text = f'  {key}: {_format_meta_value(before_value)}'
                lines.append([DiffSpan(text, "removed")])
                continue
            if kind == "added" and after_value is not None:
                text = f'  {key}: {_format_meta_value(after_value)}'
                lines.append([DiffSpan(text, "added")])
                continue
            if kind == "changed":
                display = after_value if after_value is not None else diff_value
                text = f'  {key}: {_format_meta_value(display)}'
                lines.append([DiffSpan(text, "changed")])
                continue

        if before_value is not None:
            text = f'  {key}: {_format_meta_value(before_value)}'
            lines.append([DiffSpan(text, "normal")])

    return lines


def _posting_amount_changed(index: DiffIndex, i: int) -> bool:
    return (
        f"root.postings[{i}].units.number" in index.fields
        or f"root.postings[{i}].units.currency" in index.fields
    )


def _posting_line_spans(
    before_txn, after_txn, index: DiffIndex
) -> list[tuple[list[DiffSpan], list[DiffSpan]]]:
    lines: list[tuple[list[DiffSpan], list[DiffSpan]]] = []
    after_postings = after_txn.postings or []

    for i, before_posting in enumerate(before_txn.postings or []):
        after_posting = after_postings[i] if i < len(after_postings) else before_posting
        account_path = f"root.postings[{i}].account"
        account_span = _span_for_field(
            account_path,
            before_posting.account,
            after_posting.account,
            index,
        )

        before_amount = _format_amount(before_posting)
        after_amount = _format_amount(after_posting)
        if _posting_amount_changed(index, i):
            amount_span = DiffSpan(after_amount, "changed")
        else:
            amount_span = DiffSpan(before_amount, "normal")

        account_spans = [DiffSpan("  ", "normal"), account_span, DiffSpan("    ", "normal")]
        amount_spans = [amount_span]
        lines.append((account_spans, amount_spans))

    return lines

