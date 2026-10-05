"""Run the Action with -I to isolate imports from the lab checkout."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ptgit.action_runner import main

raise SystemExit(main())
