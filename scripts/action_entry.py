"""Trusted Action entry point. Use -I to exclude the PR's import paths."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ptgit.action_runner import main

raise SystemExit(main())
