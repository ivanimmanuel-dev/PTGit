"""Static checks for common configuration and topology problems."""

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import ipaddress
import re

from .model import Snapshot


@dataclass(frozen=True, order=True)
class Finding:
    severity: str
    code: str
    location: str
    message: str

    def to_dict(self):
        return asdict(self)


def lint(snapshot: Snapshot) -> list[Finding]:
    findings = []
    addresses = defaultdict(set)
    names = {d.name for d in snapshot.devices}
    connected = set()
    interfaces = {}
    access_vlans = {}
    for diagnostic in snapshot.diagnostics:
        findings.append(Finding("error" if diagnostic.startswith("Duplicate") else "warning",
                                "MODEL_DIAGNOSTIC", "lab", diagnostic))

    def add_address(value, location):
        try:
            ip = ipaddress.ip_interface(value)
        except ValueError:
            findings.append(Finding("error", "INVALID_IP", location, f"Invalid IP address or mask: {value}"))
            return
        if not ip.ip.is_unspecified:
            addresses[str(ip.ip)].add(location)
        if ip.version == 4 and ip.network.prefixlen < 31 and ip.ip in {ip.network.network_address, ip.network.broadcast_address}:
            findings.append(Finding("warning", "RESERVED_HOST_IP", location,
                                    f"{ip} uses the subnet or broadcast address."))

    for device in snapshot.devices:
        defined_vlans = {"1", "1002", "1003", "1004", "1005"}
        defined_vlans.update(v.get("number", v.get("id", "")) for v in device.vlans)
        for block in device.config:
            if re.fullmatch(r"vlan \d+", block.header):
                defined_vlans.add(block.header[5:])
        for block in device.config:
            if not block.header.startswith("interface "):
                continue
            port = block.header[10:]
            location = f"{device.name}:{port}"
            commands = [line.strip() for line in block.lines]
            interfaces[(device.name, port)] = commands
            for line in commands:
                match = re.match(r"ip address (\S+)(?: (\S+))?", line)
                if match and match[1] not in {"dhcp", "negotiated"}:
                    value = match[1]
                    if "/" not in value:
                        value += "/" + (match[2] or "invalid-mask")
                    add_address(value, location)
                match6 = re.match(r"ipv6 address (\S+)", line)
                if match6 and "/" in match6[1]:
                    add_address(match6[1], location)
                vlan = re.fullmatch(r"switchport access vlan (\d+)", line)
                if vlan:
                    access_vlans[(device.name, port)] = vlan[1]
                    if len(vlan[1]) > 4 or not 1 <= int(vlan[1]) <= 4094:
                        findings.append(Finding("error", "INVALID_VLAN", location, f"VLAN {vlan[1]} is outside 1..4094."))
                    elif vlan[1] not in defined_vlans:
                        findings.append(Finding("warning", "UNDEFINED_ACCESS_VLAN", location,
                                                f"Access VLAN {vlan[1]} is absent from the local VLAN database/config."))
        # IOS addresses already cover router/switch interfaces; hosts use hardware IP fields.
        if not device.config:
            for port in device.ports:
                value = port.settings.get("ip", "")
                if value and value != "0.0.0.0":
                    add_address(value + "/" + port.settings.get("mask", "invalid-mask"), f"{device.name}:{port.name}")
    usage = defaultdict(list)
    for link, count in Counter(snapshot.links).items():
        location = f"{link.a.device}:{link.a.port} <-> {link.b.device}:{link.b.port}"
        if count > 1:
            findings.append(Finding("error", "DUPLICATE_LINK", location, f"Identical cable appears {count} times."))
        for end in (link.a, link.b):
            if end.device not in names:
                findings.append(Finding("error", "DANGLING_LINK", location, f"Cannot resolve endpoint {end.device}."))
            connected.add(end.device)
            usage[end].append(location)
            commands = interfaces.get((end.device, end.port), [])
            last_state = next((line for line in reversed(commands) if line in {"shutdown", "no shutdown"}), None)
            if last_state == "shutdown":
                findings.append(Finding("warning", "CONNECTED_SHUTDOWN", f"{end.device}:{end.port}",
                                        "A cable is attached to an administratively shut interface."))
        left = access_vlans.get((link.a.device, link.a.port))
        right = access_vlans.get((link.b.device, link.b.port))
        if left and right and left != right:
            # Different access VLANs may be intentional; do not call this an error.
            findings.append(Finding("warning", "ACCESS_VLAN_MISMATCH", location,
                                    f"Access VLANs differ ({left} vs {right}); confirm this is intentional."))
    for end, links in usage.items():
        if len(links) > 1 and end.port != "?":
            findings.append(Finding("warning", "PORT_REUSED", f"{end.device}:{end.port}",
                                    "The same port participates in multiple cables."))
    for address, locations in addresses.items():
        if len(locations) > 1:
            findings.append(Finding("warning", "DUPLICATE_IP", ", ".join(sorted(locations)),
                                    f"{address} is assigned more than once; separate VRFs/networks may make this intentional."))
    if len(snapshot.devices) > 1:
        for name in names - connected:
            findings.append(Finding("info", "NO_CABLE", name,
                                    "No modeled cable; wireless or deliberately isolated devices may be valid."))
    return sorted(set(findings))


def format_finding(finding: Finding) -> str:
    from .render import visible
    label = {"warning": "WARN", "error": "ERROR", "info": "INFO"}[finding.severity]
    locations = finding.location.split(", ") if finding.code == "DUPLICATE_IP" else [finding.location]
    return "\n".join([f"{label} {finding.code}", "", visible(finding.message), "",
                      *("  " + visible(location) for location in locations)])
