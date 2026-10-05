import copy
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from ptgit.config import parse_config
from ptgit.decoder import load_xml
from ptgit.errors import PTGitError
from ptgit.model import parse_snapshot
from ptgit.render import diff, show, change_groups
from ptgit.lint import lint

ROOT = Path(__file__).resolve().parents[1]


class ReleaseRegressionTests(unittest.TestCase):
    def snapshot(self):
        return parse_snapshot(ET.parse(ROOT / "examples/new.xml").getroot())

    def test_repeated_interface_contexts_keep_their_order(self):
        a = parse_config(["interface Gi0/1", " shutdown", "!", "interface Gi0/1", " no shutdown"])
        b = parse_config(["interface Gi0/1", " no shutdown", "!", "interface Gi0/1", " shutdown"])
        self.assertNotEqual(a, b)

    def test_route_map_order_is_meaningful(self):
        a = parse_config(["route-map TEST permit 10", " match ip address 10", "!", "route-map TEST deny 20"])
        b = parse_config(["route-map TEST deny 20", "!", "route-map TEST permit 10", " match ip address 10"])
        self.assertNotEqual(a, b)

    def test_duplicate_generated_label_does_not_hide_change(self):
        a = self.snapshot()
        a.devices[1].name = "R1"
        extra = copy.deepcopy(a.devices[0])
        extra.name = "R1 [duplicate 1]"
        a.devices.append(extra)
        b = copy.deepcopy(a)
        b.devices[0].model = "NewModel"
        self.assertIn("NewModel", diff(a, b))

    def test_control_character_and_literal_escape_are_distinct(self):
        a, b = self.snapshot(), self.snapshot()
        a.devices[0].name, b.devices[0].name = "Router\x03", r"Router\x03"
        self.assertNotEqual(show(a), show(b))
        self.assertTrue(diff(a, b))

    def test_render_ambiguity_never_suppresses_modeled_change(self):
        a, b = self.snapshot(), self.snapshot()
        a.devices[0].kind, a.devices[0].model = "Router (2911)", ""
        self.assertNotEqual(a.semantic_dict(), b.semantic_dict())
        self.assertNotEqual(show(a), show(b))
        self.assertTrue(diff(a, b))

    def test_large_numeric_ids_fail_cleanly(self):
        root = ET.parse(ROOT / "examples/new.xml").getroot()
        for engine in root.findall("NETWORK/DEVICES/DEVICE/ENGINE"):
            engine.remove(engine.find("SAVE_REF_ID"))
        root.find("NETWORK/LINKS/LINK/CABLE/FROM").text = "1" * 5000
        snapshot = parse_snapshot(root)
        self.assertTrue(any(f.code == "DANGLING_LINK" for f in lint(snapshot)))

    def test_xml_depth_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "deep.xml"
            path.write_text("<PACKETTRACER5><NETWORK>" + "<x>" * 130 + "</x>" * 130 + "</NETWORK></PACKETTRACER5>")
            with self.assertRaisesRegex(PTGitError, "limit"):
                load_xml(path)

    def test_deterministic_small_malformed_corpus_is_contained(self):
        rng = random.Random(10)
        original = (ROOT / "examples/new.pkt").read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.pkt"
            for _ in range(24):
                data = bytearray(original)
                point = rng.randrange(len(data))
                data[point] ^= rng.randrange(1, 256)
                path.write_bytes(data)
                with self.assertRaises(PTGitError):
                    load_xml(path)

    def test_semantic_budgets_reject_small_fixture_with_reduced_limits(self):
        # Lower the limits to exercise each guard with the ordinary fixture.
        for name, value in (("MAX_DEVICES", 1), ("MAX_LINKS", 0),
                            ("MAX_NAME_CHARS", 1), ("MAX_FIELD_CHARS", 3),
                            ("MAX_CONFIG_LINES", 2)):
            with self.subTest(name=name), patch("ptgit.model." + name, value):
                with self.assertRaises(PTGitError):
                    self.snapshot()
        with patch("ptgit.limits.MAX_MODEL_BYTES", 128):
            with self.assertRaisesRegex(PTGitError, "Expanded semantic"):
                self.snapshot()

    def test_budgeted_diff_preserves_changes_and_order(self):
        a, b = ["same", "old", "tail"], ["same", "new", "extra", "tail"]
        with patch("ptgit.render.MAX_MATCH_CELLS", 1), \
                patch("ptgit.render.difflib.SequenceMatcher", side_effect=AssertionError("unbounded alignment")):
            groups = list(change_groups(a, b))
        changed = [(tag, a[i:j], b[k:l]) for group in groups for tag, i, j, k, l in group if tag != "equal"]
        self.assertEqual(changed, [("replace", ["old"], ["new", "extra"])])

    def test_shared_memory_reference_is_ambiguous(self):
        root = ET.parse(ROOT / "examples/new.xml").getroot()
        for engine in root.findall("NETWORK/DEVICES/DEVICE/ENGINE"):
            ET.SubElement(engine, "MEM_ADDR").text = "shared"
        cable = root.find("NETWORK/LINKS/LINK/CABLE")
        cable.find("FROM").text = "missing"
        ET.SubElement(cable, "FROM_DEVICE_MEM_ADDR").text = "shared"
        snapshot = parse_snapshot(root)
        self.assertTrue(any("<unresolved:" in end.device for link in snapshot.links for end in (link.a, link.b)))

    def test_unmodeled_asset_does_not_consume_scalar_budget(self):
        root = ET.parse(ROOT / "examples/new.xml").getroot()
        ET.SubElement(root, "UNMODELED_IMAGE_ASSET").text = "image-data" * 10
        with patch("ptgit.model.MAX_FIELD_CHARS", 80):
            self.assertEqual(parse_snapshot(root).semantic_dict(), self.snapshot().semantic_dict())
