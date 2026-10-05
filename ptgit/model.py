"""Extract configuration and topology from Packet Tracer XML."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from .config import Block, interface_name, parse_config
from .decoder import load_xml
from .errors import PTGitError
from .limits import (MAX_FIELD_CHARS, MAX_NAME_CHARS, MAX_DEVICES, MAX_LINKS,
                     MAX_CONFIG_LINES, check_model_budget)


def text(node: ET.Element, path: str, default: str = "") -> str:
    value = (node.findtext(path) or default).strip()
    if len(value) > MAX_FIELD_CHARS:
        raise PTGitError("Field exceeds the 65,536-character limit.")
    return value


@dataclass
class Port:
    name: str
    settings: dict[str, str] = field(default_factory=dict)


@dataclass
class Device:
    name: str
    kind: str
    model: str
    power: str
    config: list[Block]
    ports: list[Port]
    vlans: list[dict[str, str]]
    settings: dict[str, str]


@dataclass(frozen=True, order=True)
class Endpoint:
    device: str
    port: str


@dataclass(frozen=True, order=True)
class Link:
    a: Endpoint
    b: Endpoint
    kind: str


@dataclass
class Snapshot:
    packet_tracer_version: str
    devices: list[Device]
    links: list[Link]
    diagnostics: list[str]
    config_source: str = "running"

    def to_dict(self) -> dict:
        return {"schema_version": 1, **asdict(self)}

    def semantic_dict(self) -> dict:
        result = self.to_dict()
        result.pop("packet_tracer_version")
        return result


PORT_FIELDS = {
    "IP": "ip", "SUBNET": "mask", "IPV6_LINK_LOCAL": "ipv6_link_local",
    "PORT_GATEWAY": "gateway", "PORT_DNS": "dns", "PORT_DHCP_ENABLE": "dhcp",
    "IPV6_ENABLED": "ipv6_enabled", "IPV6_ADDRESS_AUTOCONFIG": "ipv6_autoconfig",
}


def ports_from(engine: ET.Element) -> list[Port]:
    ports = []
    counts: Counter = Counter()
    for port in engine.findall(".//PORT"):
        if len(port) == 0 and not port.get("name"):
            continue
        # Hardware TYPE labels such as eCopperFastEthernet lack IOS port numbers.
        base = text(port, "NAME") or text(port, "PORTNAME") or port.get("name", "")
        if not base:
            base = text(port, "TYPE", "unnamed-port")
            counts[base] += 1
            base += f"[{counts[base]}]"
        settings = {name: text(port, tag) for tag, name in PORT_FIELDS.items()
                    if text(port, tag)}
        ipv6 = [text(node, ".") for node in port.findall("IPV6_ADDRESSES/*") if text(node, ".")]
        if ipv6:
            settings["ipv6_addresses"] = ", ".join(sorted(ipv6))
        # Inventory every hardware port, but keep runtime MAC, counters, and
        # negotiated link state out of semantic comparison.
        ports.append(Port(interface_name(base), settings))
    return sorted(ports, key=lambda p: (p.name, json.dumps(p.settings, sort_keys=True)))


def parse_snapshot(root: ET.Element, config_source: str = "running") -> Snapshot:
    if config_source not in {"running", "startup"}:
        raise PTGitError("Config source must be running or startup.")
    network = root.find("NETWORK")
    if network is None:
        raise PTGitError("Missing NETWORK element.")
    raw_devices = network.findall(".//DEVICES/DEVICE")
    if len(raw_devices) > MAX_DEVICES:
        raise PTGitError("Lab exceeds the 4,096-device limit.")
    devices = []
    diagnostics = []
    refs: dict[str, list[str]] = defaultdict(list)
    memories: dict[str, set[str]] = defaultdict(set)
    names_in_order = []
    config_line_count = 0
    for index, raw in enumerate(raw_devices):
        engine = raw.find("ENGINE")
        if engine is None:
            raise PTGitError(f"Device {index + 1} is missing its ENGINE element.")
        name = text(engine, "NAME") or f"<unnamed-device-{index + 1}>"
        if len(name) > MAX_NAME_CHARS:
            raise PTGitError("Device name exceeds the 256-character limit.")
        if not text(engine, "NAME"):
            diagnostics.append(f"Device {index + 1} has no name.")
        names_in_order.append(name)
        ref = text(engine, "SAVE_REF_ID")
        if ref:
            refs[ref].append(name)
        for path in ("WORKSPACE/LOGICAL/DEV_ADDR", "WORKSPACE/LOGICAL/MEM_ADDR", "ENGINE/MEM_ADDR"):
            value = text(raw, path)
            if value:
                memories[value].add(name)
        kind_node = engine.find("TYPE")
        kind = text(engine, "TYPE", "Unknown")
        model = kind_node.get("model", "") if kind_node is not None else ""
        config_node = engine.find("RUNNINGCONFIG" if config_source == "running" else "STARTUPCONFIG")
        config_lines = []
        if config_node is not None:
            for line in config_node.findall("LINE"):
                if len(line.text or "") > MAX_FIELD_CHARS:
                    raise PTGitError("Configuration line exceeds the 65,536-character limit.")
                config_lines.extend((line.text or "").replace("\r\n", "\n").split("\n"))
                if config_line_count + len(config_lines) > MAX_CONFIG_LINES:
                    raise PTGitError("Lab exceeds the 50,000-configuration-line limit.")
        config_line_count += len(config_lines)
        settings = {}
        for path, key in (("GATEWAY", "gateway"), ("GATEWAYV6", "gateway_v6"),
                          ("DNS_CLIENT/SERVER_IP", "dns"), ("DNS_CLIENT/SERVER_IPV6", "dns_v6")):
            if text(engine, path):
                settings[key] = text(engine, path)
        vlans = []
        for vlan in engine.findall("VLANS/VLAN"):
            # Preserve every scalar field of each VLAN database entry.
            values = {**vlan.attrib, **{child.tag.lower(): (child.text or "").strip()
                      for child in vlan if len(child) == 0}}
            if values:
                vlans.append(values)
        devices.append(Device(name, kind, model, text(engine, "POWER", "true"),
                              parse_config(config_lines), ports_from(engine),
                              sorted(vlans, key=lambda v: json.dumps(v, sort_keys=True)), settings))
    for name, count in Counter(names_in_order).items():
        if count > 1:
            diagnostics.append(f"Duplicate device name {name!r}: {count} devices; endpoint identity is ambiguous.")
    for ref, values in refs.items():
        if len(values) > 1:
            diagnostics.append(f"Duplicate device reference used by {', '.join(sorted(values))}.")

    def resolve(cable: ET.Element, side: str) -> str:
        value = text(cable, side)
        if value in refs and len(refs[value]) == 1:
            return refs[value][0]
        memory = text(cable, f"{side}_DEVICE_MEM_ADDR")
        if memory in memories and len(memories[memory]) == 1:
            return next(iter(memories[memory]))
        # Positional references are a separate schema, used when no save refs exist.
        if not refs and value.isascii() and value.isdecimal() and len(value) <= 10 and int(value) < len(names_in_order):
            return names_in_order[int(value)]
        return f"<unresolved:{value or memory or '?'}>"

    links = []
    raw_links = network.findall(".//LINKS/LINK")
    if len(raw_links) > MAX_LINKS:
        raise PTGitError("Lab exceeds the 16,384-link limit.")
    for raw in raw_links:
        cable = raw.find("CABLE")
        if cable is None:
            digest = hashlib.sha256(ET.tostring(raw)).hexdigest()[:16]
            diagnostics.append(f"Unmodeled link {text(raw, 'TYPE', 'unknown')} (XML fingerprint {digest}).")
            continue
        port_nodes = cable.findall("PORT")
        port_names = [interface_name((node.text or "").strip()) for node in port_nodes]
        if len(port_names) != 2 or not all(port_names):
            diagnostics.append("A cable does not have exactly two named ports.")
        port_names = (port_names + ["?", "?"])[:2]
        ends = sorted([Endpoint(resolve(cable, "FROM"), port_names[0]),
                       Endpoint(resolve(cable, "TO"), port_names[1])])
        links.append(Link(ends[0], ends[1], text(cable, "TYPE") or text(raw, "TYPE", "unknown")))
    snapshot = Snapshot(text(root, "VERSION", "unknown"), devices, links, diagnostics, config_source)
    check_model_budget(snapshot)
    devices.sort(key=lambda d: (d.name.casefold(), d.name, json.dumps(asdict(d), sort_keys=True)))
    snapshot.links.sort()
    snapshot.diagnostics.sort()
    return snapshot


def load_snapshot(path: str | Path, config_source: str = "running") -> Snapshot:
    return parse_snapshot(load_xml(path), config_source)
