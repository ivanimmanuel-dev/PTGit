"""Normalize interface names and IP masks while preserving IOS command order."""

from dataclasses import dataclass, asdict
from collections import Counter
import ipaddress
import re


@dataclass
class Block:
    header: str
    lines: list[str]

    def to_dict(self):
        return asdict(self)


def interface_name(value: str) -> str:
    value = value.strip()
    match = re.fullmatch(r"([A-Za-z-]+)\s*(\d.*)", value)
    if not match:
        return value
    prefixes = {
        "g": "GigabitEthernet", "gi": "GigabitEthernet", "gig": "GigabitEthernet",
        "gigabitethernet": "GigabitEthernet", "f": "FastEthernet", "fa": "FastEthernet",
        "fastethernet": "FastEthernet", "e": "Ethernet", "eth": "Ethernet", "ethernet": "Ethernet",
        "s": "Serial", "se": "Serial", "serial": "Serial", "lo": "Loopback", "loopback": "Loopback",
        "vl": "Vlan", "vlan": "Vlan", "po": "Port-channel", "port-channel": "Port-channel",
        "te": "TenGigabitEthernet", "tengigabitethernet": "TenGigabitEthernet",
    }
    return prefixes.get(match[1].lower(), match[1]) + match[2]


def normalize_command(value: str) -> str:
    value = value.rstrip(" \t\r\n")
    stripped = value.lstrip(" \t")
    indent = value[:len(value) - len(stripped)].replace("\t", " ")
    if stripped.startswith("interface "):
        return indent + "interface " + interface_name(stripped[10:])
    match = re.fullmatch(r"ip address (\S+) (\d+\.\d+\.\d+\.\d+)(.*)", stripped)
    if match:
        try:
            address = ipaddress.IPv4Interface(f"{match[1]}/{match[2]}")
            return indent + f"ip address {address}{match[3]}"
        except ValueError:
            pass
    return value


def parse_config(lines: list[str]) -> list[Block]:
    blocks: list[Block] = []
    active = None
    banner_delimiter = None
    for raw in lines:
        # A banner is data; do not reinterpret !, end, or indentation in it.
        if banner_delimiter is not None:
            active.lines.append(raw.rstrip("\r\n"))
            if banner_delimiter in raw:
                banner_delimiter = None
            continue
        line = normalize_command(raw)
        stripped = line.strip(" \t")
        if not stripped or stripped == "!":
            active = None
            continue
        if stripped == "end":
            active = None
            continue
        if not line[0].isspace() or active is None:
            active = Block(stripped, [])
            blocks.append(active)
            banner = re.match(r"banner\s+\S+\s+(.+)", stripped)
            if banner:
                payload = banner[1]
                delimiter = "^C" if payload.startswith("^C") else payload[0]
                if delimiter not in payload[len(delimiter):]:
                    banner_delimiter = delimiter
        else:
            active.lines.append(line)
    # Only move well-understood independent contexts. Everything else keeps its
    # relative order, including numbered ACLs and route-map statements.
    fixed = [b for b in blocks if not b.header.startswith(("interface ", "vlan "))]
    independent = [b for b in blocks if b.header.startswith(("interface ", "vlan "))]
    if any(count > 1 for count in Counter(b.header for b in independent).values()):
        return blocks
    return fixed + sorted(independent, key=lambda b: (b.header, b.lines))
