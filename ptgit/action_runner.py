"""Compare Packet Tracer blobs in Git and generate workflow reports."""

import argparse
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from . import __version__
from .decoder import MAX_INPUT
from .errors import PTGitError

SHA = re.compile(r"[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?\Z")


def git(repo: Path, *args: str) -> bytes:
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}
    result = subprocess.run(["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", str(repo), *args],
                            capture_output=True, env=env, timeout=30)
    if result.returncode:
        raise PTGitError("Git could not read the requested history. Use checkout with fetch-depth: 0.")
    return result.stdout


def resolve_sha(repo, value):
    if not SHA.fullmatch(value):
        raise PTGitError("Action base/head must be full hexadecimal commit SHAs.")
    result = git(repo, "rev-parse", "--verify", value + "^{commit}").decode().strip()
    if not SHA.fullmatch(result):
        raise PTGitError("Git returned an invalid commit ID.")
    return result


def changes(repo, base, head):
    raw = git(repo, "diff", "--raw", "-z", "--no-abbrev", "--no-ext-diff", "--no-textconv",
              "--no-color", "--find-renames=50%", "--diff-filter=ADMRCT", base, head, "--")
    tokens = raw.split(b"\0")
    result, index = [], 0
    while index < len(tokens) and tokens[index]:
        fields = tokens[index].decode("ascii").split()
        index += 1
        if len(fields) != 5 or not fields[0].startswith(":"):
            raise PTGitError("Unexpected Git change record.")
        old_mode, new_mode, old_blob, new_blob, status = fields
        old_path = tokens[index].decode("utf-8", "surrogateescape")
        index += 1
        new_path = old_path
        if status[0] in "RC":
            new_path = tokens[index].decode("utf-8", "surrogateescape")
            index += 1
        if not (old_path.lower().endswith(".pkt") or new_path.lower().endswith(".pkt")):
            continue
        result.append({"path": new_path, "previous_path": old_path if old_path != new_path else None,
                       "change": status[0], "old_mode": old_mode[1:], "new_mode": new_mode,
                       "old_blob": old_blob, "new_blob": new_blob})
    return sorted(result, key=lambda item: (item["path"], item["previous_path"] or ""))


def extract(repo, blob, mode, target):
    if set(blob) == {"0"}:
        return "-"
    if mode not in {"100644", "100755"}:
        raise PTGitError("Only regular .pkt blobs are supported; symlinks/submodules are not followed.")
    if not SHA.fullmatch(blob):
        raise PTGitError("Invalid blob ID.")
    size = int(git(repo, "cat-file", "-s", blob))
    if size > MAX_INPUT:
        raise PTGitError("Input exceeds the 16 MiB limit.")
    data = git(repo, "cat-file", "blob", blob)
    if len(data) != size:
        raise PTGitError("Blob length changed unexpectedly.")
    target.write_bytes(data)
    return str(target)


def redact(value):
    # Mask common IOS credential commands in both JSON and rendered output.
    if isinstance(value, str):
        lines = []
        for line in value.splitlines(keepends=True):
            previous = ""
            for match in re.finditer(r"\S+", line):
                word = match[0].lower()
                if word in {"secret", "password", "pre-shared-key", "wpa-psk", "key-string"} or \
                        (word == "community" and previous == "snmp-server"):
                    ending = "\n" if line.endswith("\n") else ""
                    line = line[:match.end()] + " <redacted>" + ending
                    break
                previous = word
            lines.append(line)
        return "".join(lines)
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    return value


def compare_blob_pair(repo, entry, timeout, worker):
    row = {key: entry[key] for key in ("path", "previous_path", "change")}
    try:
        with tempfile.TemporaryDirectory(prefix="ptgit-blobs-") as folder:
            folder = Path(folder)
            old = extract(repo, entry["old_blob"], entry["old_mode"], folder / "before.pkt")
            new = extract(repo, entry["new_blob"], entry["new_mode"], folder / "after.pkt")
            process = subprocess.run([sys.executable, "-I", str(worker), old, new],
                                     capture_output=True, timeout=timeout)
            if process.returncode:
                try:
                    reason = json.loads(process.stdout)["error"]
                except (ValueError, KeyError):
                    reason = f"Comparison process exited with code {process.returncode}."
                raise PTGitError(reason)
            row.update(json.loads(process.stdout))
            row["status"] = "ok"
    except subprocess.TimeoutExpired:
        row.update(status="error", error=f"Comparison exceeded {timeout} seconds.")
    except (PTGitError, OSError, ValueError) as exc:
        row.update(status="error", error=str(exc))
    return redact(row)


def code(value):
    # HTML-escape inside pre to keep file contents from injecting Markdown/HTML.
    return "<pre>" + html.escape(value, quote=True) + "</pre>"


def summary(report):
    lines = ["# PTGit — Packet Tracer changes"]
    if not report["files"]:
        lines.append("No changed `.pkt` files.")
    for row in report["files"]:
        # Never interpolate untrusted paths into heading/URL/Markdown syntax.
        lines.extend(["## Lab", code(row["path"])])
        if row["previous_path"]:
            lines.extend(["Previously:", code(row["previous_path"])])
        if row["status"] != "ok":
            lines.extend(["**Could not compare this file.**", code(row["error"])])
            continue
        counts = row["counts"]
        lines.extend([code("\n".join([
            f"Devices changed: {counts['devices_changed']}",
            f"Devices added:   {counts['devices_added']}",
            f"Devices removed: {counts['devices_removed']}",
            f"Links added:     {counts['links_added']}",
            f"Links removed:   {counts['links_removed']}",
            f"Warnings:        {counts['warnings']}",
            f"Lint errors:     {counts['lint_errors']}"])),
            code(row["diff"] or "No changes.")])
        if row["diff_truncated"]:
            lines.append("Showing the first 80,000 diff characters. Run ptgit diff locally for the full output.")
        if row["findings"]:
            lines.append(code("\n".join(f"{f['severity'].upper()} {f['code']} {f['location']}: {f['message']}"
                                        for f in row["findings"])))
        if row["findings_truncated"]:
            lines.append("Only the first 100 lint findings are displayed; counts include all findings.")
    rendered = "\n\n".join(lines) + "\n"
    # GitHub permits at most 1 MiB per step summary. Keep well below that bound,
    # truncating only between complete lab sections so HTML always stays closed.
    if len(rendered.encode("utf-8", "backslashreplace")) > 900_000:
        return "# PTGit — Packet Tracer changes\n\nDownload the JSON artifact to view this report; it exceeds the Job Summary size limit.\n"
    return rendered


def analyze(repo, base, head, max_files=40, timeout=30, worker=None):
    base, head = resolve_sha(repo, base), resolve_sha(repo, head)
    merge_base = git(repo, "merge-base", base, head).decode().strip()
    entries = changes(repo, merge_base, head)
    if len(entries) > max_files:
        raise PTGitError(f"{len(entries)} changed .pkt files exceed the configured limit of {max_files}; split the PR or raise max-files (up to 100).")
    worker = worker or Path(__file__).resolve().parents[1] / "scripts/action_worker.py"
    return {"schema_version": 1, "ptgit_version": __version__, "base": base, "head": head,
            "merge_base": merge_base, "files": [compare_blob_pair(repo, entry, timeout, worker) for entry in entries]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(os.environ.get("GITHUB_WORKSPACE", ".")))
    parser.add_argument("--base", default=os.environ.get("PTGIT_BASE", ""))
    parser.add_argument("--head", default=os.environ.get("PTGIT_HEAD", ""))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if not args.base or not args.head:
            event_path = os.environ.get("GITHUB_EVENT_PATH")
            if not event_path:
                raise PTGitError("Pass --base/--head or run on a pull_request event.")
            event = json.loads(Path(event_path).read_text(encoding="utf-8"))
            pr = event.get("pull_request", {})
            args.base = args.base or pr.get("base", {}).get("sha", "")
            args.head = args.head or pr.get("head", {}).get("sha", "")
        max_files = int(os.environ.get("PTGIT_MAX_FILES", "40"))
        timeout = int(os.environ.get("PTGIT_TIMEOUT", "30"))
        if not 1 <= max_files <= 100 or not 1 <= timeout <= 120:
            raise PTGitError("max-files must be 1..100 and timeout-seconds 1..120.")
        output = args.output_dir or Path(tempfile.mkdtemp(prefix="ptgit-report-", dir=os.environ.get("RUNNER_TEMP")))
        output.mkdir(parents=True, exist_ok=True)
        report = analyze(args.repo, args.base, args.head, max_files, timeout)
        report_path, summary_path = output / "report.json", output / "summary.md"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
        rendered = summary(report)
        summary_path.write_text(rendered, encoding="utf-8", errors="backslashreplace")
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8", errors="backslashreplace") as stream:
                stream.write(rendered)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
                stream.write(f"report={report_path.resolve()}\nsummary={summary_path.resolve()}\nchanged-files={len(report['files'])}\n")
        count = len(report["files"])
        label = "lab" if count == 1 else "labs"
        print(f"PTGit inspected {count} changed {label}.")
        return int(any(row["status"] == "error" or
                       (os.environ.get("PTGIT_FAIL_ON_LINT", "false").lower() == "true" and row.get("counts", {}).get("lint_errors", 0))
                       for row in report["files"]))
    except (PTGitError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"PTGit: {exc}", file=sys.stderr)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
                stream.write("# PTGit — comparison failed\n\n" + code(str(exc)))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
