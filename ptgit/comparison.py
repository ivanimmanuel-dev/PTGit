"""Compare lab snapshots and summarize changes."""

from collections import Counter, defaultdict
from dataclasses import asdict
import json

from .model import Snapshot
from .lint import lint
from .render import diff


def compare(old: Snapshot, new: Snapshot) -> dict:
    def devices(snapshot):
        grouped = defaultdict(list)
        for device in snapshot.devices:
            grouped[device.name].append(json.dumps(asdict(device), sort_keys=True))
        return {name: sorted(values) for name, values in grouped.items()}
    a, b = devices(old), devices(new)
    added = removed = changed = 0
    for name in a.keys() | b.keys():
        left, right = a.get(name, []), b.get(name, [])
        added += max(0, len(right) - len(left))
        removed += max(0, len(left) - len(right))
        changed += sum(x != y for x, y in zip(left, right))
    old_links, new_links = Counter(old.links), Counter(new.links)
    findings = [finding.to_dict() for finding in lint(new)]
    return {
        "semantic_changed": old.semantic_dict() != new.semantic_dict(),
        "counts": {"devices_added": added, "devices_removed": removed, "devices_changed": changed,
                   "links_added": sum((new_links - old_links).values()),
                   "links_removed": sum((old_links - new_links).values()),
                   "warnings": sum(f["severity"] == "warning" for f in findings),
                   "lint_errors": sum(f["severity"] == "error" for f in findings)},
        "diff": diff(old, new), "findings": findings,
    }
