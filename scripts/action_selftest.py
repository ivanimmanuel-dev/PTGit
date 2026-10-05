"""Prepare or assert the reusable Action's integration scenario in CI."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def prepare():
    folder = ROOT / ".ptgit-action-selftest"
    if folder.exists():
        raise SystemExit("Self-test folder already exists; use a disposable checkout.")
    folder.mkdir()
    git("config", "--local", "user.name", "PT Git self-test")
    git("config", "--local", "user.email", "selftest@example.invalid")
    lab = folder / "lab with spaces.pkt"
    shutil.copyfile(FIXTURES / "old.pkt", lab)
    git("add", "--", str(lab))
    git("commit", "-qm", "PT Git Action fixture before")
    base = git("rev-parse", "HEAD")
    shutil.copyfile(FIXTURES / "new.pkt", lab)
    git("add", "--", str(lab))
    git("commit", "-qm", "PT Git Action fixture after")
    head = git("rev-parse", "HEAD")
    output = f"base={base}\nhead={head}\n"
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            stream.write(output)
    print(output, end="")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "assert"))
    parser.add_argument("report", nargs="?")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    else:
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        assert len(report["files"]) == 1
        row = report["files"][0]
        assert row["status"] == "ok", row
        assert row["counts"]["devices_changed"] == 2, row
        assert row["counts"]["links_added"] == 1, row
        assert "10.10.20.1/24" in row["diff"], row
        print("PASS: reusable Action scenario")
