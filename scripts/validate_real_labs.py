"""Validate before/after lab pairs created in Packet Tracer."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ptgit.model import load_snapshot
from ptgit.comparison import compare
from ptgit.errors import PTGitError


def validate(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results = []
    build = manifest.get("packet_tracer_build", "")
    if not build or "REPLACE" in build:
        raise ValueError("Record the exact Packet Tracer version/build from Help > About first.")
    if manifest.get("provenance") != "packet-tracer-gui":
        raise ValueError("This harness requires pairs produced by the real Packet Tracer GUI.")
    for case in manifest["cases"]:
        result = {"id": case["id"], "packet_tracer_build": build, "config": case.get("config", "running")}
        try:
            before, after = [(manifest_path.parent / case[key]).resolve() for key in ("before", "after")]
            if before.suffix.lower() != ".pkt" or after.suffix.lower() != ".pkt":
                raise ValueError("GUI validation pairs must use .pkt files.")
            a, b = [load_snapshot(p, result["config"]) for p in (before, after)]
            comparison = compare(a, b)
            result.update(before_sha256=hashlib.sha256(before.read_bytes()).hexdigest(),
                          after_sha256=hashlib.sha256(after.read_bytes()).hexdigest(),
                          before_saved_version=a.packet_tracer_version, after_saved_version=b.packet_tracer_version,
                          semantic_changed=comparison["semantic_changed"], counts=comparison["counts"])
            if comparison["semantic_changed"] != case["expect_semantic_change"]:
                raise ValueError("Observed semantic-change result differs from the manifest expectation.")
            for value in case.get("contains", []):
                if value not in comparison["diff"]:
                    raise ValueError(f"Expected diff fragment absent: {value!r}")
            result["status"] = "passed"
        except (OSError, PTGitError, ValueError) as exc:
            result.update(status="failed", error=str(exc))
        results.append(result)
    return {"schema_version": 1, "provenance": "operator-declared packet-tracer-gui",
            "packet_tracer_build": build, "cases": results,
            "passed": bool(results) and all(r["status"] == "passed" for r in results)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = validate(args.manifest)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"{sum(r['status'] == 'passed' for r in report['cases'])}/{len(report['cases'])} real-file cases passed.")
        raise SystemExit(0 if report["passed"] else 1)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"Validation setup: {exc}\n")
