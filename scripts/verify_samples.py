"""Optional read-only smoke test against a supplied sample folder.

Usage: python scripts/verify_samples.py /path/to/samples > verification.json
Prints only filenames/counts/results, never configs. Does not copy input labs.
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ptgit.model import load_snapshot
from ptgit.render import show
from ptgit.errors import PTGitError

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("folder", type=Path)
parser.add_argument("--limit", type=int, default=20)
args = parser.parse_args()
if not args.folder.is_dir() or args.limit < 1:
    parser.error("Provide a sample directory and a positive limit.")
paths = sorted(args.folder.rglob("*.pkt"))[:args.limit]
if not paths:
    parser.error("No .pkt files found.")
results = []
for path in paths:
    result = {"file": path.relative_to(args.folder).as_posix()}
    try:
        snapshot = load_snapshot(path)
        result.update(status="passed", saved_version=snapshot.packet_tracer_version,
                      devices=len(snapshot.devices), cables=len(snapshot.links),
                      unresolved_endpoints=sum(e.device.startswith("<unresolved:") for l in snapshot.links for e in (l.a, l.b)),
                      diagnostics=len(snapshot.diagnostics), text_characters=len(show(snapshot)))
    except (PTGitError, OSError) as exc:
        result.update(status="failed", error=str(exc))
    results.append(result)
print(json.dumps(results, indent=2))
raise SystemExit(int(any(r["status"] == "failed" for r in results)))
