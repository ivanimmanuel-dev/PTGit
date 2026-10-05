"""Generate test fixtures from XML using an Unpacket checkout."""

import argparse
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("unpacket", type=Path, help="Path to an Unpacket source checkout")
args = parser.parse_args()
sys.path.insert(0, str(args.unpacket.resolve()))
from repacket import compress_qt, obf_stage2, encrypt_pkt, obf_stage1

fixtures = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
for name in ("old", "new"):
    xml = (fixtures / f"{name}.xml").read_bytes()
    pkt = obf_stage1(encrypt_pkt(obf_stage2(compress_qt(xml))))
    (fixtures / f"{name}.pkt").write_bytes(pkt)
    print(f"{name}.pkt: {len(pkt)} bytes")
    if name == "old":
        # Unpacket's existing symmetric stage-2 transform also matches the
        # legacy XOR wrapper documented by pktforge.
        (fixtures / "old-legacy.pkt").write_bytes(obf_stage2(compress_qt(xml)))
