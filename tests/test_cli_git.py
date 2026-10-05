import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def run_cli(*args, cwd=ROOT):
    env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONUTF8": "1"}
    return subprocess.run([sys.executable, "-m", "ptgit", *map(str, args)],
                          cwd=cwd, env=env, text=True, encoding="utf-8", capture_output=True)


class CLITests(unittest.TestCase):
    def test_help_and_version(self):
        self.assertEqual(run_cli("--help").returncode, 0)
        self.assertEqual(run_cli("--version").stdout.strip(), "ptgit 0.1.1")

    def test_show_export_lint_and_no_input_mutation(self):
        path = FIXTURES / "new.pkt"
        before = path.read_bytes()
        self.assertIn("R1", run_cli("show", path).stdout)
        exported = run_cli("export", path, "--json")
        self.assertEqual(exported.returncode, 0, exported.stderr)
        self.assertEqual(len(json.loads(exported.stdout)["devices"]), 2)
        checked = run_cli("lint", path, "--json")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(checked.stdout)["findings"], [])
        self.assertEqual(before, path.read_bytes())

    def test_diff_exit_codes(self):
        old, new = FIXTURES / "old.pkt", FIXTURES / "new.pkt"
        self.assertEqual(run_cli("diff", old, new).returncode, 0)
        self.assertEqual(run_cli("diff", old, new, "--exit-code").returncode, 1)
        self.assertEqual(run_cli("diff", new, new, "--exit-code").returncode, 0)

    def test_missing_file_and_corrupt_container(self):
        result = run_cli("show", ROOT / "absent.pkt")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "broken.pkt"
            data = bytearray((FIXTURES / "new.pkt").read_bytes())
            data[len(data) // 2] ^= 1
            path.write_bytes(data)
            result = run_cli("show", path)
            self.assertEqual(result.returncode, 2)
            self.assertIn("authentication failed", result.stderr)
            self.assertEqual(result.stdout, "")

    def test_extensionless_textconv(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "git-blob"
            shutil.copyfile(FIXTURES / "new.pkt", path)
            result = run_cli("textconv", path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Topology", result.stdout)

    def test_init_requires_repository(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run_cli("init", temp)
            self.assertEqual(result.returncode, 2)
            self.assertIn("git init", result.stderr)


@unittest.skipUnless(shutil.which("git"), "Git not installed")
class GitIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ptgit repo spaces ")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "PT Git test")
        self.git("config", "user.email", "test@example.invalid")

    def git(self, *args):
        env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
               "GIT_TERMINAL_PROMPT": "0"}
        result = subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True,
                                text=True, encoding="utf-8", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_init_is_idempotent_and_preserves_attributes(self):
        attrs = self.repo / ".gitattributes"
        attrs.write_text("*.png binary\n*.txt text eol=lf\n", encoding="utf-8")
        self.assertEqual(run_cli("init", self.repo).returncode, 0)
        first = attrs.read_bytes()
        self.assertEqual(run_cli("init", self.repo).returncode, 0)
        self.assertEqual(attrs.read_bytes(), first)
        self.assertIn("*.png binary", attrs.read_text())
        self.assertEqual(self.git("config", "--local", "--get", "diff.ptgit.cachetextconv").strip(), "false")
        self.assertIn("lab.pkt: text: unset", self.git("check-attr", "text", "--", "lab.pkt"))

    def test_real_git_diff_and_staged_diff_use_textconv(self):
        setup = run_cli("init", self.repo)
        self.assertEqual(setup.returncode, 0, setup.stderr)
        path = self.repo / "lab with spaces.pkt"
        shutil.copyfile(FIXTURES / "old.pkt", path)
        self.git("add", ".")
        self.git("commit", "-qm", "before")
        shutil.copyfile(FIXTURES / "new.pkt", path)
        output = self.git("diff", "--", path.name)
        self.assertIn("switchport access vlan 20", output)
        self.assertNotIn("Binary files", output)
        self.git("add", path.name)
        output = self.git("diff", "--cached", "--", path.name)
        self.assertIn("10.10.20.1/24", output)
        # -text must retain exact binary bytes in the index.
        raw = subprocess.check_output(["git", "-C", str(self.repo), "show", ":" + path.name])
        self.assertEqual(raw, path.read_bytes())

    def test_git_diff_ignores_layout_only(self):
        self.assertEqual(run_cli("init", self.repo).returncode, 0)
        path = self.repo / "lab.pkt"
        path.write_bytes((FIXTURES / "new.xml").read_bytes())
        self.git("add", ".")
        self.git("commit", "-qm", "before")
        path.write_bytes(path.read_bytes().replace(b"<X>800</X>", b"<X>9999</X>"))
        self.assertEqual(self.git("diff", "--", "lab.pkt"), "")

    def test_conflicting_driver_requires_force_without_partial_writes(self):
        self.git("config", "diff.ptgit.textconv", "existing-converter")
        result = run_cli("init", self.repo)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.repo / ".gitattributes").exists())
        self.assertEqual(self.git("config", "diff.ptgit.textconv").strip(), "existing-converter")
        self.assertEqual(run_cli("init", self.repo, "--force").returncode, 0)

    def test_moved_source_driver_is_refreshed_and_other_drivers_survive(self):
        self.git("config", "diff.other.textconv", "other-converter")
        parent = self.repo / "installations"
        first, moved = parent / "original source", parent / "moved source"
        shutil.copytree(ROOT / "ptgit", first / "ptgit", ignore=shutil.ignore_patterns("__pycache__"))

        def setup(source, *args):
            env = {**os.environ, "PYTHONPATH": str(source), "PYTHONUTF8": "1"}
            return subprocess.run([sys.executable, "-m", "ptgit", "init", str(self.repo), *args],
                                  cwd=source, env=env, capture_output=True, text=True)

        self.assertEqual(setup(first).returncode, 0)
        # Both resolved paths remain inside this temporary repository.
        self.assertIn(self.repo.resolve(), first.resolve().parents)
        self.assertIn(self.repo.resolve(), moved.resolve().parents)
        first.rename(moved)
        self.assertEqual(setup(moved).returncode, 2)
        self.assertEqual(setup(moved, "--force").returncode, 0)
        self.assertEqual(self.git("config", "diff.other.textconv").strip(), "other-converter")
        path = self.repo / "moved lab.pkt"
        shutil.copyfile(FIXTURES / "old.pkt", path)
        self.git("add", ".gitattributes", path.name)
        self.git("commit", "-qm", "before")
        shutil.copyfile(FIXTURES / "new.pkt", path)
        self.assertIn("10.10.20.1/24", self.git("diff", "--", path.name))

    def test_global_config_is_unchanged(self):
        config = self.repo / "test-global-config"
        original = b"[diff \"unrelated\"]\n\ttextconv = keep-this\n"
        config.write_bytes(original)
        with patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"}):
            result = run_cli("init", self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(config.read_bytes(), original)

    def test_external_diff_driver_is_not_silently_overridden(self):
        self.git("config", "diff.ptgit.command", "existing-external-driver")
        result = run_cli("init", self.repo, "--force")
        self.assertEqual(result.returncode, 2)
        self.assertIn("overrides textconv", result.stderr)
        self.assertFalse((self.repo / ".gitattributes").exists())


if __name__ == "__main__":
    unittest.main()
