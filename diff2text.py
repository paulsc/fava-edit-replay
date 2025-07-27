import re

def format_diff(delta):
    """
    Format a DeepDiff delta as a list of readable English text lines.
    Args:
        delta: The delta object containing the changes
    Returns:
        A list of strings, each describing a change
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

