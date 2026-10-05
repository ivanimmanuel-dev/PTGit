"""Record actual CLI/Git output with a short scripted playback timeline."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def record(destination):
    destination.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONUTF8": "1",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_PAGER": "cat"}
    events, transcript, tick = [], [], 0.0
    with tempfile.TemporaryDirectory(prefix="ptgit demo ") as folder:
        repo = Path(folder)

        def run(args, label=None):
            nonlocal tick
            completed = subprocess.run(args, cwd=repo, env=env, text=True,
                                       encoding="utf-8", capture_output=True, timeout=60)
            if completed.returncode:
                raise RuntimeError(completed.stderr)
            if label:
                text = "$ " + label + "\n" + completed.stdout
                transcript.append(text)
                events.append([tick, "o", text.replace("\n", "\r\n")])
                tick += 4.0
            return completed.stdout

        run(["git", "init", "-q"])
        run(["git", "config", "--local", "user.name", "PT Git demo"])
        run(["git", "config", "--local", "user.email", "demo@example.invalid"])
        shutil.copyfile(ROOT / "examples/old.pkt", repo / "lab.pkt")
        run(["git", "add", "lab.pkt"])
        run(["git", "commit", "-qm", "Initial lab"])
        shutil.copyfile(ROOT / "examples/new.pkt", repo / "lab.pkt")
        run(["git", "diff", "--", "lab.pkt"], "git diff -- lab.pkt")
        run([sys.executable, "-m", "ptgit", "diff", str(ROOT / "examples/old.pkt"), "lab.pkt"],
            "ptgit diff old.pkt lab.pkt")
        run([sys.executable, "-m", "ptgit", "init"])
        run(["git", "diff", "--", "lab.pkt"], "git diff -- lab.pkt  # after ptgit init")
    header = {"version": 2, "width": 108, "height": 36,
              "title": "PT Git — from binary changes to readable diffs",
              "env": {"TERM": "xterm-256color", "SHELL": "scripted"}}
    (destination / "demo.cast").write_text("\n".join(json.dumps(item, ensure_ascii=True)
                                         for item in [header, *events]) + "\n", encoding="utf-8", newline="\n")
    (destination / "demo.txt").write_text("\n".join(transcript), encoding="utf-8", newline="\n")
    # The HTML uses textContent only; no command output becomes markup.
    payload = json.dumps(events, ensure_ascii=True).replace("<", "\\u003c")
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>PT Git demo</title><style>body{background:#101621;color:#dce5f5;max-width:1050px;margin:5vh auto;padding:24px;font:16px system-ui}h1{font-size:48px;margin:0}p{color:#a4b7cd}button{border:0;border-radius:7px;padding:10px 16px;background:#7ef0ba;color:#10201a;font-weight:700;cursor:pointer}pre{background:#070c13;border:1px solid #263446;padding:24px;min-height:400px;overflow:auto;font:14px/1.55 Consolas,monospace;white-space:pre-wrap}small{color:#93a4b9}</style>
<h1>PT Git</h1><p>Meaningful version control for Packet Tracer labs.</p><button id="play">Replay 12-second demo</button>
<pre id="screen"></pre><small>Recorded CLI output using the bundled test fixtures. Playback advances every four seconds.</small>
<script>const events=EVENTS;let timers=[];const screen=document.getElementById('screen');function play(){timers.forEach(clearTimeout);timers=[];screen.textContent='';events.forEach(e=>timers.push(setTimeout(()=>{screen.textContent=e[2];},e[0]*1000)));}document.getElementById('play').onclick=play;play();</script></html>'''
    (destination / "index.html").write_text(page.replace("EVENTS", payload), encoding="utf-8", newline="\n")
    print(f"Recorded actual output in {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/demo")
    record(parser.parse_args().output)
