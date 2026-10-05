"""CLI contract: 0 success, 1 requested diff/lint failure, 2 input/setup error."""

import argparse
import json
import sys

from . import __version__
from .errors import PTGitError
from .gitsetup import initialize
from .lint import lint, format_finding
from .model import load_snapshot
from .render import diff, show, visible


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="ptgit", description="Readable diffs for Packet Tracer labs.")
    result.add_argument("--version", action="version", version=f"ptgit {__version__}")
    commands = result.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Enable .pkt diffs in a Git repository")
    init.add_argument("directory", nargs="?", default=".")
    init.add_argument("--force", action="store_true", help="Replace an existing ptgit driver")
    comparison = commands.add_parser("diff", help="Compare topology and device configurations")
    comparison.add_argument("old")
    comparison.add_argument("new")
    comparison.add_argument("--exit-code", action="store_true", help="Exit 1 when changes exist")
    for name, help_text in (("show", "Read device configuration and topology"),
                            ("lint", "Check IPs, VLANs, and cable connections"),
                            ("export", "Export lab data as JSON"),
                            ("textconv", "Convert a lab for Git diffs")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("file")
        if name in {"lint", "export"}:
            command.add_argument("--json", action="store_true", help="Write machine-readable JSON")
        if name == "lint":
            command.add_argument("--strict", action="store_true", help="Warnings also cause exit 1")
        if name != "textconv":
            command.add_argument("--config", choices=("running", "startup"), default="running")
    comparison.add_argument("--config", choices=("running", "startup"), default="running")
    return result


def main(argv=None) -> int:
    # UTF-8 is important for Git pipes on Windows; only reconfigure real streams.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            root = initialize(args.directory, args.force)
            print(f"PTGit enabled in {root}.")
            return 0
        config = getattr(args, "config", "running")
        if args.command == "diff":
            output = diff(load_snapshot(args.old, config), load_snapshot(args.new, config))
            if output:
                print(output, end="")
            else:
                print("No changes.")
            return 1 if output and args.exit_code else 0
        snapshot = load_snapshot(args.file, config)
        if args.command in {"show", "textconv"}:
            print(show(snapshot), end="")
        elif args.command == "export":
            print(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
        else:
            findings = lint(snapshot)
            if args.json:
                print(json.dumps({"schema_version": 1, "findings": [f.to_dict() for f in findings]},
                                 indent=2, ensure_ascii=False, sort_keys=True))
            else:
                for f in findings:
                    print(format_finding(f) + "\n")
                errors = sum(f.severity == "error" for f in findings)
                warnings = sum(f.severity == "warning" for f in findings)
                error_label = "error" if errors == 1 else "errors"
                warning_label = "warning" if warnings == 1 else "warnings"
                print(f"{errors} {error_label}, {warnings} {warning_label}.")
            return int(any(f.severity == "error" or (args.strict and f.severity == "warning") for f in findings))
        return 0
    except (PTGitError, OSError) as exc:
        print(f"ptgit: {visible(str(exc))}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
