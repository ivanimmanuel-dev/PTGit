"""Legacy wrapper from pktforge, commit 5a29c522e99e7ed18f591430cb25a5b0b6f1df3a.

Copyright (c) 2026 I Nyoman Widiyasa Jayananda. MIT; see pktforge-LICENSE.
Copied legacy_xor_schedule; decompression delegated to the bounded Qt reader.
"""

from .unpacket.pt_crypto import uncompress_qt


def legacy_xor_schedule(data: bytes) -> bytes:
    size = len(data)
    out = bytearray()

    for byte in data:
        out.append((byte ^ size) & 0xFF)
        size -= 1

    return bytes(out)


def try_legacy_decompile(data: bytes) -> bytes:
    return uncompress_qt(legacy_xor_schedule(data))
