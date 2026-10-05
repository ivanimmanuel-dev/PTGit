"""An absolute-path entry point so source checkouts work in other Git repos."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ptgit.cli import main

raise SystemExit(main(["textconv", *sys.argv[1:]]))
