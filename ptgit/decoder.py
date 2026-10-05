"""Decode modern and legacy Packet Tracer containers into bounded XML."""

from pathlib import Path
import xml.etree.ElementTree as ET

from ._vendor.unpacket.pt_crypto import decrypt_pkt
from ._vendor.pktforge_legacy import try_legacy_decompile
from .errors import PTGitError

MAX_INPUT = 16 * 1024 * 1024
MAX_XML = 64 * 1024 * 1024
MAX_ELEMENTS = 250_000
MAX_DEPTH = 128


def load_xml(path: str | Path) -> ET.Element:
    path = Path(path)
    if path.suffix.lower() == ".pka":
        raise PTGitError("Activity (.pka) files are not supported. Use a .pkt lab.")
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_INPUT + 1)
    except OSError as exc:
        raise PTGitError(f"Cannot read {path}: {exc.strerror or exc}") from exc
    if len(data) > MAX_INPUT:
        raise PTGitError("Input exceeds the 16 MiB limit.")
    if not data:
        raise PTGitError("The input file is empty.")
    # Content detection also works with Git's extensionless temporary files.
    prefix = data.removeprefix(b"\xef\xbb\xbf").lstrip(b" \t\r\n")
    if not prefix.startswith((b"<PACKETTRACER5", b"<?xml", b"<!DOCTYPE", b"<!ENTITY")):
        try:
            data = decrypt_pkt(data)
        except (ValueError, IndexError, OverflowError) as exc:
            try:
                data = try_legacy_decompile(data)
            except ValueError:
                raise PTGitError(f"Cannot decode Packet Tracer lab: {exc}. "
                                 "The legacy container did not match either. "
                                 "Try saving a copy as .pkt in Packet Tracer.") from exc
    if len(data) > MAX_XML:
        raise PTGitError("Decoded XML exceeds the 64 MiB limit.")
    try:
        xml = data.decode("utf-8-sig")
    except UnicodeError as exc:
        raise PTGitError("Decoded XML must use UTF-8.") from exc
    # Packet Tracer banners can contain raw C0 delimiters, forbidden in XML 1.0.
    # Map only present controls to unused private-use characters, then restore text.
    used = set(xml)
    mapping = {}
    point = 0xE000
    for char in sorted(set(xml)):
        if ord(char) < 32 and char not in "\t\r\n":
            while point <= 0xF8FF and chr(point) in used:
                point += 1
            if point > 0xF8FF:
                raise PTGitError("No safe replacement characters remain for XML control delimiters.")
            mapping[char] = chr(point)
            point += 1
    for original, safe in mapping.items():
        xml = xml.replace(original, safe)
    if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        raise PTGitError("DTD and entity declarations are not supported.")
    try:
        parser = ET.XMLPullParser(events=("start", "end"))
        depth = count = 0
        root = None
        for offset in range(0, len(xml), 8192):
            parser.feed(xml[offset:offset + 8192])
            for event, node in parser.read_events():
                if event == "start":
                    depth += 1
                    count += 1
                    if root is None:
                        root = node
                    if depth > MAX_DEPTH or count > MAX_ELEMENTS:
                        raise PTGitError("XML exceeds the 128-level or 250,000-element limit.")
                else:
                    depth -= 1
        parser.close()
    except ET.ParseError as exc:
        raise PTGitError(f"Invalid Packet Tracer XML: {exc}") from exc
    if root is None or root.tag != "PACKETTRACER5" or root.find("NETWORK") is None:
        raise PTGitError("Expected PACKETTRACER5 XML with a NETWORK element.")
    for node in root.iter():
        if node.text:
            for original, safe in mapping.items():
                node.text = node.text.replace(safe, original)
    return root
