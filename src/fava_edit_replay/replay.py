import json
from pathlib import Path
from typing import NamedTuple, Any
import yaml
from yaml.loader import SafeLoader
from fava_edit_replay.diff2text import format_diff

import logging
logger = logging.getLogger("edit_replay")

class LineNumberLoader(SafeLoader):
    """Custom YAML loader that adds line numbers to loaded objects."""
    def construct_mapping(self, node, deep=False):
        mapping = super().construct_mapping(node, deep=deep)
        mapping['lineno'] = node.start_mark.line + 1  # 1-based
        return mapping

class Replay(NamedTuple):
    lineno: int           # line number in the db file
    time_filter: str      # time filter
    account_filter: str   # account filter
    advanced_filter: str  # advanced filter
    diff: str             # diff to apply as json string
    diff_readable: str    # diff to apply as readable text

def load_replays_with_lineno(replays_path: Path) -> list[dict]:
    """Load all replays from YAML file with line numbers added."""
    if not replays_path.exists():
        return []
    
    with replays_path.open("r", encoding="utf-8") as f:
        raw_replays = yaml.load(f, Loader=LineNumberLoader) or []
    return raw_replays

def save_replay_to_file(replay: Replay, replays_path: Path) -> str:
    """Save a Replay NamedTuple to the YAML file at replays_path."""
    replays = []
    if replays_path.exists():
        with replays_path.open("r", encoding="utf-8") as f:
            replays = yaml.safe_load(f) or []

    replay_data = {
        'time_filter': replay.time_filter,
        'account_filter': replay.account_filter,
        'advanced_filter': replay.advanced_filter,
        'diff': replay.diff,
    }
    replays.append(replay_data)
    with replays_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(replays, f, allow_unicode=True, sort_keys=True)

def load_replays_from_file(replays_path: Path) -> list[Replay]:
    """Load all saved replays from a YAML file as a list of Replay objects, with line numbers."""
    raw_replays = load_replays_with_lineno(replays_path)
    replays = []
    for replay in raw_replays:
        diff = replay.get('diff', '')
        diff_readable = ', '.join(format_diff(json.loads(diff)))
        replays.append(
            Replay(
                lineno=replay.get('lineno', -1),
                time_filter=replay.get('time_filter', ''),
                account_filter=replay.get('account_filter', ''),
                advanced_filter=replay.get('advanced_filter', ''),
                diff=diff,
                diff_readable=diff_readable
            )
        )
    return replays 

def delete_replay_by_lineno(lineno: int, replays_path: Path) -> None:
    """Delete a replay by line number from the YAML file."""
    raw_replays = load_replays_with_lineno(replays_path)
    
    # Find the replay with the matching line number and remove it
    filtered_replays = []
    for replay in raw_replays:
        if replay.get('lineno') != lineno:
            # Remove the lineno field before saving back
            replay_copy = replay.copy()
            replay_copy.pop('lineno', None)
            filtered_replays.append(replay_copy)
    
    # Write back the updated replays
    with replays_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(filtered_replays, f, allow_unicode=True, sort_keys=True) 