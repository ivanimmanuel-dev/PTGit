"""Stable text conversion and human-readable semantic diffs."""

from collections import Counter
import difflib
import json
import hashlib

from .model import Device, Snapshot

MAX_MATCH_CELLS = 1_000_000


def change_groups(a, b):
    if len(a) * len(b) <= MAX_MATCH_CELLS:
        yield from difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_grouped_opcodes(2)
        return
    # A linear prefix/suffix comparison preserves every changed line when a
    # detailed alignment would exceed the work budget. Context may be broader.
    prefix = 0
    while prefix < min(len(a), len(b)) and a[prefix] == b[prefix]:
        prefix += 1
    suffix = 0
    while suffix < min(len(a), len(b)) - prefix and a[-1 - suffix] == b[-1 - suffix]:
        suffix += 1
    end_a, end_b = len(a) - suffix, len(b) - suffix
    group = []
    if prefix:
        group.append(("equal", max(0, prefix - 2), prefix, max(0, prefix - 2), prefix))
    group.append(("replace", prefix, end_a, prefix, end_b))
    if suffix:
        group.append(("equal", end_a, end_a + min(2, suffix), end_b, end_b + min(2, suffix)))
    yield group


def visible(value: str) -> str:
    # Never emit terminal escapes or embedded line breaks from a saved lab.
    return "".join("\\\\" if c == "\\" else c if (ord(c) >= 32 and ord(c) != 127 and not 0x80 <= ord(c) < 0xA0)
                   else f"\\x{ord(c):02x}" for c in value)


def device_lines(device: Device) -> list[str]:
    lines = [f"type {device.kind}" + (f" ({device.model})" if device.model else ""),
             f"power {device.power}"]
    for key, value in sorted(device.settings.items()):
        lines.append(f"{key} {value}")
    for vlan in device.vlans:
        lines.append("vlan-database " + json.dumps(vlan, sort_keys=True, ensure_ascii=False))
    for port in device.ports:
        lines.append(f"port {port.name}")
        lines.extend(f"  {key} {value}" for key, value in sorted(port.settings.items()))
    for block in device.config:
        lines.append(block.header)
        lines.extend(block.lines)
    return [visible(line) for line in lines]


def sections(snapshot: Snapshot) -> list[tuple[str, list[str]]]:
    counts = Counter(d.name for d in snapshot.devices)
    seen = Counter()
    result = []
    for device in snapshot.devices:
        seen[device.name] += 1
        label = device.name if counts[device.name] == 1 else f"{device.name} [duplicate {seen[device.name]}]"
        result.append((visible(label), device_lines(device)))
    result.append(("Topology", [visible(f"{link.a.device}:{link.a.port} <-> "
                                     f"{link.b.device}:{link.b.port} [{link.kind}]")
                                for link in snapshot.links]))
    if snapshot.diagnostics:
        result.append(("Diagnostics", [visible(d) for d in snapshot.diagnostics]))
    return result


def show(snapshot: Snapshot) -> str:
    lines = [f"PT Git semantic snapshot v1 ({snapshot.config_source} config)"]
    for title, content in sections(snapshot):
        lines.extend(["", title])
        lines.extend("  " + line for line in content)
    # Fingerprint the complete modeled structure, including context boundaries
    # and duplicate identities that a human display may otherwise conflate.
    canonical = json.dumps(snapshot.semantic_dict(), sort_keys=True, ensure_ascii=True).encode()
    lines.extend(["", "Modeled fields SHA-256: " + hashlib.sha256(canonical).hexdigest()])
    return "\n".join(lines) + "\n"


def diff(old: Snapshot, new: Snapshot) -> str:
    if old.semantic_dict() == new.semantic_dict():
        return ""
    # Index by section position within name to retain devices named 'Topology'.
    def indexed(snapshot):
        result = {}
        counts = Counter()
        for i, (name, lines) in enumerate(sections(snapshot)):
            role = "device" if i < len(snapshot.devices) else "metadata"
            identity = snapshot.devices[i].name if role == "device" else name
            counts[(role, identity)] += 1
            result[(role, identity, counts[(role, identity)])] = (name, lines)
        return result
    before, after = indexed(old), indexed(new)
    result = []
    for key in sorted(before.keys() | after.keys()):
        label_a, a = before.get(key, ("", []))
        label_b, b = after.get(key, ("", []))
        if a == b and key in before and key in after:
            continue
        title = label_b or label_a
        if key not in before:
            title += " (added)"
        elif key not in after:
            title += " (removed)"
        result.append(title)
        # Context identifies which interface/ACL changed without a whole config dump.
        for group_index, group in enumerate(change_groups(a, b)):
            if group_index:
                result.append("  ...")
            start = group[0][1]
            if start < len(a) and a[start].startswith(" "):
                # A short diff hunk must still identify its IOS/port context.
                for index in range(start - 1, -1, -1):
                    if a[index] and not a[index][0].isspace():
                        result.append("  " + a[index])
                        break
            for tag, i1, i2, j1, j2 in group:
                if tag == "equal":
                    result.extend("  " + line for line in a[i1:i2])
                if tag in {"delete", "replace"}:
                    result.extend("- " + line for line in a[i1:i2])
                if tag in {"insert", "replace"}:
                    result.extend("+ " + line for line in b[j1:j2])
        result.append("")
    if result:
        return "\n".join(result).rstrip() + "\n"
    # Rare display ambiguity must never turn a real modeled change into a clean diff.
    return "Modeled structure\n- " + json.dumps(old.semantic_dict(), sort_keys=True) + \
        "\n+ " + json.dumps(new.semantic_dict(), sort_keys=True) + "\n"
