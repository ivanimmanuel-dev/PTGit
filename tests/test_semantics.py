import copy
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from ptgit.config import parse_config
from ptgit.decoder import load_xml
from ptgit.errors import PTGitError
from ptgit.lint import lint
from ptgit.model import load_snapshot, parse_snapshot
from ptgit.render import diff, show

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def example(name="new"):
    return ET.parse(FIXTURES / f"{name}.xml").getroot()


class SemanticTests(unittest.TestCase):
    def test_actual_binary_decoder_matches_xml(self):
        for name in ("old", "new"):
            binary = load_snapshot(FIXTURES / f"{name}.pkt")
            xml = load_snapshot(FIXTURES / f"{name}.xml")
            self.assertEqual(binary.to_dict(), xml.to_dict())

    def test_requested_changes_are_visible(self):
        output = diff(parse_snapshot(example("old")), parse_snapshot(example()))
        for value in ("+ interface GigabitEthernet0/1", "+  ip address 10.10.20.1/24",
                      "-  switchport access vlan 10", "+  switchport access vlan 20",
                      "+ R1:GigabitEthernet0/1 <-> SW2:GigabitEthernet0/1"):
            self.assertIn(value, output)

    def test_legacy_decoder_matches_modern(self):
        self.assertEqual(load_snapshot(FIXTURES / "old-legacy.pkt").to_dict(),
                         load_snapshot(FIXTURES / "old.pkt").to_dict())

    def test_layout_ids_device_order_and_cable_direction_do_not_change_text(self):
        before = example()
        after = copy.deepcopy(before)
        devices = after.find("NETWORK/DEVICES")
        devices[:] = list(reversed(list(devices)))
        for device in devices:
            ref = device.find("ENGINE/SAVE_REF_ID")
            ref.text += "-new"
        cable = after.find("NETWORK/LINKS/LINK/CABLE")
        cable.find("FROM").text = "sw2-new"
        cable.find("TO").text = "r1-new"
        after.find("NETWORK/DEVICES/DEVICE[2]/WORKSPACE/LOGICAL/X").text = "50000"
        after.find("NETWORK/DEVICES/DEVICE[2]/WORKSPACE/LOGICAL/MEM_ADDR").text = "200000"
        after.find("VERSION").text = "9.99"
        self.assertEqual(show(parse_snapshot(before)), show(parse_snapshot(after)))

    def test_positional_links(self):
        root = example()
        for engine in root.findall("NETWORK/DEVICES/DEVICE/ENGINE"):
            engine.remove(engine.find("SAVE_REF_ID"))
        cable = root.find("NETWORK/LINKS/LINK/CABLE")
        cable.find("FROM").text, cable.find("TO").text = "0", "1"
        self.assertEqual(parse_snapshot(example()).links, parse_snapshot(root).links)

    def test_interface_reordering_and_abbreviation_are_ignored(self):
        left = parse_config(["interface Gi0/1", " ip address 1.2.3.4 255.255.255.0", "!", "interface Fa0/1", " shutdown"])
        right = parse_config(["interface FastEthernet0/1", " shutdown", "!", "interface GigabitEthernet0/1", " ip address 1.2.3.4/24"])
        self.assertEqual(left, right)

    def test_acl_order_is_preserved(self):
        a = parse_config(["ip access-list extended TEST", " permit ip any any", " deny ip any any"])
        b = parse_config(["ip access-list extended TEST", " deny ip any any", " permit ip any any"])
        self.assertNotEqual(a, b)

    def test_diff_includes_interface_context_for_long_blocks(self):
        before, after = parse_snapshot(example()), parse_snapshot(example())
        before.devices[0].config = parse_config(["interface Gi0/7"] + [f" description line {i}" for i in range(8)])
        after.devices[0].config = copy.deepcopy(before.devices[0].config)
        after.devices[0].config[0].lines[-1] = " description changed"
        output = diff(before, after)
        self.assertIn("interface GigabitEthernet0/7", output)
        self.assertIn("+  description changed", output)

    def test_global_numbered_acl_order_is_preserved(self):
        a = ["access-list 10 permit 1.1.1.1", "access-list 10 deny any"]
        self.assertNotEqual(parse_config(a), parse_config(list(reversed(a))))

    def test_banner_preserves_config_like_content(self):
        blocks = parse_config(["banner motd ^C", "!", "end", "interface Gi0/1", "^C", "hostname R1"])
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].lines, ["!", "end", "interface Gi0/1", "^C"])

    def test_vlan_database_changes_are_visible(self):
        a, b = example(), example()
        b.find("NETWORK/DEVICES/DEVICE[2]/ENGINE/VLANS/VLAN").set("name", "Changed")
        self.assertIn("Changed", diff(parse_snapshot(a), parse_snapshot(b)))

    def test_startup_is_independent(self):
        root = example()
        engine = root.find("NETWORK/DEVICES/DEVICE/ENGINE")
        startup = ET.SubElement(engine, "STARTUPCONFIG")
        ET.SubElement(startup, "LINE").text = "hostname BOOT"
        self.assertNotIn("hostname BOOT", show(parse_snapshot(root)))
        self.assertIn("hostname BOOT", show(parse_snapshot(root, "startup")))

    def test_hardware_ports_do_not_include_dhcp_references(self):
        root = example()
        engine = root.find("NETWORK/DEVICES/DEVICE/ENGINE")
        ET.SubElement(ET.SubElement(engine, "DHCP_CLIENT"), "PORT").text = "FastEthernet"
        self.assertEqual(parse_snapshot(root).devices[0].ports, [])

    def test_unknown_link_is_reported_and_changes_diff(self):
        a, b = example(), example()
        link = ET.SubElement(b.find("NETWORK/LINKS"), "LINK")
        ET.SubElement(link, "TYPE").text = "new-kind"
        snapshot = parse_snapshot(b)
        self.assertIn("Unmodeled link", diff(parse_snapshot(a), snapshot))
        self.assertTrue(any(f.code == "MODEL_DIAGNOSTIC" for f in lint(snapshot)))

    def test_missing_engine_is_not_silently_dropped(self):
        root = example()
        device = root.find("NETWORK/DEVICES/DEVICE")
        device.remove(device.find("ENGINE"))
        with self.assertRaises(PTGitError):
            parse_snapshot(root)

    def test_malformed_and_entity_xml_fail_clearly(self):
        for value in (b"", b"<PACKETTRACER5>", b"<wrong/>",
                      b'<!DOCTYPE x [<!ENTITY x "hello">]><PACKETTRACER5><NETWORK/></PACKETTRACER5>'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "lab.xml"
                path.write_bytes(value)
                with self.assertRaises(PTGitError):
                    load_xml(path)

    def test_raw_banner_controls_and_unicode_are_retained_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lab.xml"
            path.write_bytes('<PACKETTRACER5><NETWORK><DEVICES><DEVICE><ENGINE><NAME>Røuter</NAME><RUNNINGCONFIG><LINE>banner motd \x03Hi\x03</LINE></RUNNINGCONFIG></ENGINE></DEVICE></DEVICES></NETWORK></PACKETTRACER5>'.encode())
            output = show(load_snapshot(path))
            self.assertIn("Røuter", output)
            self.assertIn(r"\x03Hi\x03", output)
            self.assertNotIn("\x03", output)

    def test_lint_common_mistakes(self):
        root = example()
        config = root.find("NETWORK/DEVICES/DEVICE/ENGINE/RUNNINGCONFIG")
        config.findall("LINE")[7].text = " shutdown"
        switch = root.find("NETWORK/DEVICES/DEVICE[2]/ENGINE")
        switch.find("VLANS").clear()
        snapshot = parse_snapshot(root)
        codes = {f.code for f in lint(snapshot)}
        self.assertTrue({"CONNECTED_SHUTDOWN", "UNDEFINED_ACCESS_VLAN"} <= codes)

    def test_dangling_duplicate_cables_and_names(self):
        root = example()
        root.find("NETWORK/LINKS/LINK/CABLE/FROM").text = "missing-ref"
        links = root.find("NETWORK/LINKS")
        links.append(copy.deepcopy(links[0]))
        root.find("NETWORK/DEVICES/DEVICE[2]/ENGINE/NAME").text = "R1"
        codes = {f.code for f in lint(parse_snapshot(root))}
        self.assertTrue({"DANGLING_LINK", "DUPLICATE_LINK", "MODEL_DIAGNOSTIC"} <= codes)

    def test_invalid_and_duplicate_ip_findings(self):
        snapshot = parse_snapshot(example())
        snapshot.devices[0].config = parse_config(["interface Gi0/1", " ip address 10.0.0.1/24",
                                                   "!", "interface Gi0/2", " ip address 999.1.1.1 255.255.255.0"])
        snapshot.devices[1].config = parse_config(["interface Gi0/1", " ip address 10.0.0.1/24"])
        findings = lint(snapshot)
        self.assertTrue(any(f.code == "INVALID_IP" and f.severity == "error" for f in findings))
        self.assertTrue(any(f.code == "DUPLICATE_IP" and f.severity == "warning" for f in findings))

    def test_json_is_serializable_and_versioned(self):
        result = json.loads(json.dumps(parse_snapshot(example()).to_dict()))
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(len(result["links"]), 1)


if __name__ == "__main__":
    unittest.main()
