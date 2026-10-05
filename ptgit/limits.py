"""Limit fields and expanded snapshots before rendering."""
from dataclasses import fields, is_dataclass

from .errors import PTGitError

MAX_FIELD_CHARS = 65_536
MAX_NAME_CHARS = 256
MAX_DEVICES = 4_096
MAX_LINKS = 16_384
MAX_CONFIG_LINES = 50_000
MAX_MODEL_BYTES = 8 * 1024 * 1024


def check_model_budget(model):
    # Count repeated values on every occurrence: reference expansion must consume
    # the same budget as inline data. Fixed overhead also limits tiny objects.
    pending = [model]
    used = 0
    while pending:
        item = pending.pop()
        used += 64
        if isinstance(item, str):
            if len(item) > MAX_FIELD_CHARS:
                raise PTGitError("Field exceeds the 65,536-character limit.")
            used += len(item.encode("utf-8"))
        elif is_dataclass(item):
            pending.extend(getattr(item, f.name) for f in fields(item))
        elif isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, (list, tuple)):
            pending.extend(item)
        if used > MAX_MODEL_BYTES:
            raise PTGitError("Snapshot exceeds the 8 MiB processing limit.")
