import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from ptgit.action_runner import analyze, summary, redact
from ptgit.errors import PTGitError

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("git"), "Git required")
class ActionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ptgit action ")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "PT Git tests")
        self.git("config", "user.email", "test@example.invalid")
        for name in ("lab.pkt", "removed.pkt", "rename source.pkt"):
            shutil.copyfile(ROOT / "examples/old.pkt", self.repo / name)
        (self.repo / "removed.pkt").write_text("<PACKETTRACER5><NETWORK><DEVICES><DEVICE><ENGINE><NAME>Gone</NAME></ENGINE></DEVICE></DEVICES></NETWORK></PACKETTRACER5>")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args, input=None):
        env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
        result = subprocess.run(["git", "-C", str(self.repo), *args], input=input, env=env,
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "head")
        return self.git("rev-parse", "HEAD").strip()

    def test_modify_add_delete_rename_and_deterministic_json(self):
        shutil.copyfile(ROOT / "examples/new.pkt", self.repo / "lab.pkt")
        shutil.copyfile(ROOT / "examples/new.pkt", self.repo / "added [lab].PKT")
        (self.repo / "removed.pkt").unlink()
        (self.repo / "rename source.pkt").rename(self.repo / "renamed lab.pkt")
        head = self.commit()
        report = analyze(self.repo, self.base, head)
        self.assertEqual(len(report["files"]), 4)
        by_name = {r["path"]: r for r in report["files"]}
        self.assertEqual(by_name["lab.pkt"]["counts"]["devices_changed"], 2)
        self.assertEqual(by_name["lab.pkt"]["counts"]["links_added"], 1)
        self.assertEqual(by_name["added [lab].PKT"]["counts"]["devices_added"], 2)
        self.assertEqual(by_name["removed.pkt"]["counts"]["devices_removed"], 1)
        self.assertFalse(by_name["renamed lab.pkt"]["semantic_changed"])
        self.assertEqual(by_name["renamed lab.pkt"]["previous_path"], "rename source.pkt")
        self.assertEqual(json.dumps(report, sort_keys=True), json.dumps(analyze(self.repo, self.base, head), sort_keys=True))
        self.assertIn("Devices changed: 2", summary(report))

    def test_corrupt_lab_fails_without_hiding_other_results(self):
        (self.repo / "bad.pkt").write_bytes(b"not a packet tracer lab")
        shutil.copyfile(ROOT / "examples/new.pkt", self.repo / "lab.pkt")
        report = analyze(self.repo, self.base, self.commit())
        self.assertEqual([r["status"] for r in report["files"]], ["error", "ok"])

    def test_symlink_blob_is_not_followed(self):
        blob = self.git("hash-object", "-w", "--stdin", input="../private.pkt").strip()
        self.git("update-index", "--add", "--cacheinfo", f"120000,{blob},link.pkt")
        self.git("commit", "-qm", "symlink")
        report = analyze(self.repo, self.base, self.git("rev-parse", "HEAD").strip())
        self.assertEqual(report["files"][0]["status"], "error")
        self.assertIn("not followed", report["files"][0]["error"])

    def test_no_changed_labs_and_invalid_refs(self):
        (self.repo / "README.md").write_text("hello")
        head = self.commit()
        self.assertEqual(analyze(self.repo, self.base, head)["files"], [])
        with self.assertRaisesRegex(PTGitError, "full hexadecimal"):
            analyze(self.repo, "main", head)

    def test_file_count_cap_is_explicit(self):
        for name in ("one.pkt", "two.pkt"):
            shutil.copyfile(ROOT / "examples/new.pkt", self.repo / name)
        with self.assertRaisesRegex(PTGitError, "exceed"):
            analyze(self.repo, self.base, self.commit(), max_files=1)

    def test_worker_timeout_is_reported(self):
        worker = self.repo / "slow_worker.py"
        worker.write_text("import time\ntime.sleep(10)\n", encoding="utf-8")
        shutil.copyfile(ROOT / "examples/new.pkt", self.repo / "lab.pkt")
        report = analyze(self.repo, self.base, self.commit(), timeout=1, worker=worker)
        self.assertEqual(report["files"][0]["status"], "error")
        self.assertIn("exceeded", report["files"][0]["error"])

    def test_entry_writes_summary_outputs_and_isolates_pr_imports(self):
        shutil.copyfile(ROOT / "examples/new.pkt", self.repo / "lab.pkt")
        for name in ("json.py", "subprocess.py", "sitecustomize.py"):
            (self.repo / name).write_text("raise RuntimeError('PR import must not run')\n")
        head = self.commit()
        output = self.repo / "job-output"
        env = {**os.environ, "GITHUB_STEP_SUMMARY": str(self.repo / "summary-file"),
               "GITHUB_OUTPUT": str(self.repo / "outputs-file"), "PYTHONPATH": str(self.repo)}
        result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/action_entry.py"),
                                 "--repo", str(self.repo), "--base", self.base, "--head", head,
                                 "--output-dir", str(output)], cwd=self.repo, env=env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PT Git", (self.repo / "summary-file").read_text(encoding="utf-8"))
        self.assertIn("changed-files=1", (self.repo / "outputs-file").read_text())
        self.assertTrue((output / "report.json").exists())


class PresentationTests(unittest.TestCase):
    def test_summary_escapes_untrusted_markup(self):
        output = summary({"files": [{"path": "<img src=x>\n```", "previous_path": None,
                                     "status": "error", "error": "</pre><script>bad</script>"}]})
        self.assertNotIn("<script>", output)
        self.assertNotIn("<img", output)
        self.assertIn("&lt;script&gt;", output)

    def test_credentials_are_redacted_in_json_and_diff(self):
        output = redact({"diff": "+ enable secret 5 pretend-secret\n- username lab password old-value\n",
                         "findings": ["snmp-server community private-value ro"]})
        self.assertNotIn("pretend-secret", json.dumps(output))
        self.assertNotIn("old-value", json.dumps(output))
        self.assertNotIn("private-value", json.dumps(output))
        self.assertIn("redacted", output["diff"])

    def test_masking_retains_noncredential_lines_and_line_breaks(self):
        ordinary = "username student\n description username student profile\n"
        self.assertEqual(redact(ordinary), ordinary)
        self.assertEqual(redact("+ username student secret 5 example\nnext\n"),
                         "+ username student secret <redacted>\nnext\n")
