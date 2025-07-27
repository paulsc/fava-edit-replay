import json
from pathlib import Path
from typing import NamedTuple, Any
import yaml
from yaml.loader import SafeLoader
from edit_replay.diff2text import format_diff

import logging
logger = logging.getLogger("edit_replay")

class Replay(NamedTuple):
    lineno: int           # line number in the db file
    time_filter: str      # time filter
    account_filter: str   # account filter
    advanced_filter: str  # advanced filter
    diff: str             # diff to apply as json string
    diff_readable: str    # diff to apply as readable text

def save_replay_to_file(replay: Replay, replays_path: Path) -> str:
    """Save a Replay NamedTuple to the YAML file at replays_path."""
    replays = []
    if replays_path.exists():
        with replays_path.open("r", encoding="utf-8") as f:
            replays = yaml.safe_load(f) or []
    replays.append(replay._asdict())
    with replays_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(replays, f, allow_unicode=True, sort_keys=True)

def load_replays_from_file(replays_path: Path) -> list[Replay]:
    """Load all saved replays from a YAML file as a list of Replay objects, with line numbers."""
    class LineNumberLoader(SafeLoader):
        def construct_mapping(self, node, deep=False):
            mapping = super().construct_mapping(node, deep=deep)
            mapping['lineno'] = node.start_mark.line + 1  # 1-based
            return mapping
    replays = []
    if replays_path.exists():
        with replays_path.open("r", encoding="utf-8") as f:
            raw_replays = yaml.load(f, Loader=LineNumberLoader) or []
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