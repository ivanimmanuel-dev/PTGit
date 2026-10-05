# Decoder provenance

PT Git uses Unpacket for modern `.pkt` containers and pktforge's legacy XOR
wrapper for older files. Both run in Python without native build steps.

| Project | Commit | Use |
|---|---|---|
| [Unpacket](https://github.com/Punkcake21/Unpacket/tree/54cb6d6a9b46c6b4973356258cb8df6ae58b2ec7) | `54cb6d6a9b46c6b4973356258cb8df6ae58b2ec7` | Twofish, EAX, CMAC, CTR, and container decoding |
| [pktforge](https://github.com/Schryzon/pktforge/tree/5a29c522e99e7ed18f591430cb25a5b0b6f1df3a) | `5a29c522e99e7ed18f591430cb25a5b0b6f1df3a` | Legacy XOR wrapper |
| [packet-tracer-skill](https://github.com/20hajiyev/packet-tracer-skill/tree/03e8084eaaade9e7f37437fa701928af92826e49) | `03e8084eaaade9e7f37437fa701928af92826e49` | Evaluated as an alternative and schema reference; no code copied |

## Adaptations

Unpacket's imports are package-relative. Its Qt decompressor now enforces an
output limit, exact stored length, and complete compressed stream. A minimum
container-length check handles truncated inputs. Modern containers retain EAX
tag verification; the Twofish implementation is unchanged.

pktforge's `legacy_xor_schedule` is copied verbatim. Its decompression wrapper
uses the same bounded Qt reader as the modern path. The native compilation bridge
is not included. The installed Cisco `Outside_Nat.pkt` sample exercises this path.

## Licensing

Unpacket and pktforge provide MIT licenses. The Twofish implementation also
carries a Gladman/Edstrom permission and attribution notice. All original notices
are retained in source and distribution metadata; see
[third-party notices](../THIRD_PARTY_NOTICES.md).

The upstream encoder is used by `scripts/build_fixtures.py` to reproduce synthetic
test inputs from an explicitly supplied Unpacket checkout. PT Git's CLI is read-only.

## Validation

Encrypted and legacy fixtures are compared with their original XML in the test
suite. Additional checks use nine installed Cisco samples and one contributor
lab; see [validation results](verification.md). Sample files and contributor labs
are kept outside the repository.
