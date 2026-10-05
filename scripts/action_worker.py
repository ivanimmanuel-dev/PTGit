"""Bounded, isolated per-file comparison invoked by action_runner."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ptgit.comparison import compare
from ptgit.model import Snapshot, load_snapshot
from ptgit.errors import PTGitError


def main():
    # Apply a process memory ceiling where resource.RLIMIT_AS is available.
    # The parent enforces the comparison timeout on every platform.
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    except (ImportError, ValueError, OSError):
        pass
    snapshots = []
    try:
        for name in sys.argv[1:3]:
            snapshots.append(Snapshot("unknown", [], [], []) if name == "-" else load_snapshot(name))
        result = compare(*snapshots)
        # Artifacts remain bounded even when a lab contains extensive IOS text.
        result["diff_truncated"] = len(result["diff"]) > 80_000
        result["diff"] = result["diff"][:80_000]
        result["findings_truncated"] = len(result["findings"]) > 100
        result["findings"] = result["findings"][:100]
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 0
    except (PTGitError, OSError, ValueError, MemoryError, RecursionError) as exc:
        print(json.dumps({"error": str(exc) or type(exc).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
