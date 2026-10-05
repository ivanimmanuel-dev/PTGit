"""Install a built wheel in a fresh environment and exercise real Git outside source."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def check(wheel):
    wheel = Path(wheel).resolve()
    with tempfile.TemporaryDirectory(prefix="ptgit clean install ") as folder:
        folder = Path(folder)
        environment = folder / "environment with spaces"
        repo = folder / "network labs"
        repo.mkdir()
        venv.EnvBuilder(with_pip=True).create(environment)
        binaries = environment / ("Scripts" if os.name == "nt" else "bin")
        python = binaries / ("python.exe" if os.name == "nt" else "python")
        cli = binaries / ("ptgit.exe" if os.name == "nt" else "ptgit")
        env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
        env.update(PYTHONUTF8="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

        def run(*args, expected=0):
            result = subprocess.run(list(map(str, args)), cwd=repo, env=env,
                                    capture_output=True, text=True, encoding="utf-8", timeout=120)
            if result.returncode != expected:
                raise RuntimeError(f"{args[0]} failed ({result.returncode}): {result.stderr}\n{result.stdout}")
            return result.stdout

        run(python, "-m", "pip", "install", "--no-index", "--no-deps", wheel)
        assert run(cli, "--version").strip() == "ptgit 0.1.0"
        assert run(python, "-m", "ptgit", "--version") == run(cli, "--version")
        imported = run(python, "-c", "import ptgit; print(ptgit.__file__)").strip()
        assert environment.resolve() in Path(imported).resolve().parents, imported
        old, new = FIXTURES / "old.pkt", FIXTURES / "new.pkt"
        assert "R1" in run(cli, "show", new)
        assert json.loads(run(cli, "export", new, "--json"))["schema_version"] == 1
        assert "0 errors" in run(cli, "lint", new)
        assert "10.10.20.1/24" in run(cli, "diff", old, new, "--exit-code", expected=1)
        run("git", "init", "-q")
        run("git", "config", "--local", "user.name", "PT Git verification")
        run("git", "config", "--local", "user.email", "verification@example.invalid")
        (repo / ".gitattributes").write_text("*.txt text\n", encoding="utf-8")
        run(cli, "init")
        first = (repo / ".gitattributes").read_bytes()
        run(cli, "init")
        assert (repo / ".gitattributes").read_bytes() == first
        lab = repo / "lab with spaces.pkt"
        shutil.copyfile(old, lab)
        run("git", "add", ".")
        run("git", "commit", "-qm", "Initial lab")
        shutil.copyfile(new, lab)
        assert "switchport access vlan 20" in run("git", "diff", "--", lab.name)
        run("git", "add", lab.name)
        assert "10.10.20.1/24" in run("git", "diff", "--cached", "--", lab.name)
        # Reinstallation preserves the working driver; --force also refreshes it.
        run(python, "-m", "pip", "install", "--no-index", "--no-deps", "--force-reinstall", wheel)
        run(cli, "init", "--force")
        assert "10.10.20.1/24" in run("git", "diff", "--cached", "--", lab.name)
        print("PASS: fresh wheel, console/module, show/diff/lint/export, installed Git staged/unstaged, reinstall, paths with spaces")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel")
    check(parser.parse_args().wheel)
