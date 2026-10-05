"""Reproduce the synthetic demo binaries with an audited Unpacket checkout.

Usage: python scripts/build_fixtures.py /path/to/Unpacket
These are parser fixtures, not complete labs intended for the Cisco GUI.
"""

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit(__doc__)
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
from repacket import compress_qt, obf_stage2, encrypt_pkt, obf_stage1

root = Path(__file__).resolve().parents[1]
for name in ("old", "new"):
    xml = (root / "examples" / f"{name}.xml").read_bytes()
    pkt = obf_stage1(encrypt_pkt(obf_stage2(compress_qt(xml))))
    (root / "examples" / f"{name}.pkt").write_bytes(pkt)
    print(f"{name}.pkt: {len(pkt)} bytes")
    if name == "old":
        # Unpacket's existing symmetric stage-2 transform also matches the
        # legacy XOR wrapper documented by pktforge.
        (root / "examples/old-legacy.pkt").write_bytes(obf_stage2(compress_qt(xml)))
