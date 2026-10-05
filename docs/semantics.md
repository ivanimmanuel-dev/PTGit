# Comparison rules

PTGit compares saved configuration and topology after normalization.

## Fields

| Area | Included data |
|---|---|
| Devices | Display name, type, model, power state |
| IOS | Running or startup configuration lines |
| VLAN database | Scalar values in each entry |
| Hosts | Gateway and DNS |
| Hardware ports | IPv4 address/mask, gateway, DNS, DHCP, IPv6 addresses and selected IPv6 flags |
| Cables | Endpoint devices, port names, cable type |

Service records, files, wireless settings outside IOS, IoT programs, workspace
notes, simulation events, and activity grading are excluded.

## Normalization

`Gi0/1` becomes `GigabitEthernet0/1`; `10.10.20.1 255.255.255.0` becomes
`10.10.20.1/24`. Blank separators and trailing whitespace are removed.
Devices, cables, and unique interface/VLAN blocks are sorted.
Commands within blocks, repeated contexts, ACLs, route maps, and other IOS
commands retain their order. Large diffs can use broader replacement blocks.

Layout, internal IDs, runtime counters, generated MAC addresses, and saved
Packet Tracer version do not affect the diff.

Device identity uses the display name. Renames appear as removed/added devices
and relabeled cable endpoints. Duplicate names and unresolved endpoints produce
diagnostics. Non-cable links use an XML fingerprint. Ports without names use
their type and ordinal, such as `eCopperGigabitEthernet[1]`.

Text snapshots include a SHA-256 of the normalized data to distinguish
structures that have the same readable lines.

## Configuration and JSON

The default is running configuration. `--config startup` selects startup
configuration for `show`, `diff`, `lint`, and `export`. Git textconv and the Action
use running configuration. Saving a `.pkt` file does not copy IOS running
configuration to startup.

JSON exports use `schema_version: 1`, sorted keys, and a `config_source` field.
The saved Packet Tracer version is included as metadata.

## Lint

Checks cover duplicate names, IPs and cables, unresolved endpoints, reused ports,
invalid IPs/VLANs, undefined access VLANs, VLAN mismatches, and cabled shutdown
interfaces. Uncabled devices produce informational findings. IP and VLAN checks
use the saved configuration; they do not model routing domains or simulate traffic.
