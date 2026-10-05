"""Configure repository attributes and the local Git textconv driver."""

import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

from .errors import PTGitError

BEGIN = "# BEGIN PT Git"
END = "# END PT Git"
ATTRIBUTES = "*.pkt diff=ptgit -text\n*.PKT diff=ptgit -text"


def git(path, *args, check=True):
    try:
        result = subprocess.run(["git", "-C", str(path), *args], capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PTGitError(f"Cannot run Git: {exc}") from exc
    if check and result.returncode:
        raise PTGitError(result.stderr.strip() or "Git command failed.")
    return result


def initialize(path: str | Path = ".", force: bool = False) -> Path:
    found = git(path, "rev-parse", "--show-toplevel", check=False)
    if found.returncode:
        raise PTGitError("Run git init first, or run ptgit init inside an existing Git working tree.")
    root = Path(found.stdout.strip())
    attrs = root / ".gitattributes"
    if attrs.is_symlink():
        raise PTGitError("Refusing to replace a symlinked .gitattributes.")
    try:
        original = attrs.read_bytes() if attrs.exists() else b""
        content = original.decode("utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise PTGitError("Cannot read .gitattributes as UTF-8.") from exc
    if content.count(BEGIN) != content.count(END) or content.count(BEGIN) > 1:
        raise PTGitError("Malformed PT Git block in .gitattributes; repair it before running init.")
    if BEGIN in content:
        start, finish = content.index(BEGIN), content.index(END)
        if start > finish:
            raise PTGitError("Malformed PT Git block in .gitattributes.")
        content = content[:start] + content[finish + len(END):].lstrip("\r\n")
    # Git runs textconv through a POSIX shell, including Git for Windows.
    executable = Path(sys.executable).as_posix()
    entry = Path(__file__).with_name("textconv_entry.py").resolve().as_posix()
    command = shlex.join([executable, entry])
    desired = {"diff.ptgit.textconv": command, "diff.ptgit.binary": "true",
               "diff.ptgit.cachetextconv": "false"}
    old_values = {key: git(root, "config", "--local", "--get-all", key, check=False).stdout.splitlines()
                  for key in desired}
    current = git(root, "config", "--get", "diff.ptgit.textconv", check=False).stdout.strip()
    external = git(root, "config", "--get", "diff.ptgit.command", check=False).stdout.strip()
    if external:
        raise PTGitError("An external diff.ptgit.command overrides textconv. Remove that Git setting before init; --force only replaces the textconv driver.")
    if current and current != command and not force:
        raise PTGitError("A different ptgit textconv driver already exists. Use --force to replace it.")
    updated = (content.rstrip("\r\n") + "\n" if content else "") + f"{BEGIN}\n{ATTRIBUTES}\n{END}\n"
    # Preflight attributes before any config mutation. Preserve permissions on replacement.
    temp = None
    changed = []
    try:
        with tempfile.NamedTemporaryFile(dir=root, prefix=".ptgit-", delete=False) as stream:
            temp = Path(stream.name)
            stream.write(updated.encode("utf-8"))
        if attrs.exists():
            os.chmod(temp, attrs.stat().st_mode)
        for key, value in desired.items():
            git(root, "config", "--local", "--replace-all", key, value)
            changed.append(key)
        os.replace(temp, attrs)
    except (OSError, PTGitError) as exc:
        for key in reversed(changed):
            git(root, "config", "--local", "--unset-all", key, check=False)
            for value in old_values[key]:
                git(root, "config", "--local", "--add", key, value, check=False)
        raise PTGitError(f"Could not install PT Git: {exc}") from exc
    finally:
        if temp is not None and temp.exists():
            temp.unlink()
    return root
