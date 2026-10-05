# Comparison rules

PT Git compares a normalized view of saved configuration and topology. A clean
diff means the fields below agree; data outside this view is ignored.

## Included fields

| Area | Fields |
|---|---|
| Devices | Display name, type, model, power state |
| IOS | Saved running or startup configuration lines |
| VLAN database | Scalar values in each entry |
| Hosts | Gateway and DNS settings |
| Hardware ports | IPv4 address/mask, gateway, DNS, DHCP, selected IPv6 settings |
| Cables | Endpoint devices, port names, cable type |

IOS lines include interface settings, routes, ACLs, DHCP pools, and VLAN commands.
PT Git preserves unfamiliar commands as saved text. It does not simulate IOS.

Service records and files, wireless settings outside IOS, IoT programs, physical
workspace layout, notes, simulation events, and activity grading are outside
the comparison model.

## Normalization

Interface abbreviations are expanded: `Gi0/1` becomes `GigabitEthernet0/1`.
IOS IPv4 addresses use prefix notation: `10.10.20.1 255.255.255.0` becomes
`10.10.20.1/24`. Blank configuration separators and trailing whitespace are removed.

Devices and cable endpoints are sorted. Save IDs resolve device references but
do not appear in the comparison. Layout, runtime counters, generated MAC addresses,
and the saved Packet Tracer version are ignored.

Independent interface and VLAN blocks are sorted when their headers are unique.
Repeated contexts, commands inside blocks, ACLs, route maps, and unfamiliar
commands retain their order. Large diffs may show a broader replacement block
to keep comparison work bounded.

## Identity and diagnostics

Device identity is based on the display name. A rename appears as a removed
device and an added device, with cable endpoints relabeled accordingly. Duplicate
names are retained and reported as ambiguous.

Unnamed hardware ports use a type and ordinal, such as `eCopperGigabitEthernet[1]`.
Unresolved cable endpoints produce diagnostics. Non-cable link types use an XML
fingerprint, which may change when internal metadata changes.

Readable snapshots include a SHA-256 of the full normalized model. This keeps
structural differences visible even when two fields produce similar display text.

## JSON and configuration selection

`ptgit export` produces sorted JSON with `schema_version: 1`. It includes the saved
Packet Tracer version as metadata; comparison and textconv omit that value.

Use `--config startup` with `show`, `diff`, `lint`, or `export` to select startup
configuration. The default, Git textconv, and the Action use running configuration.
Saving a `.pkt` file and copying IOS running configuration to startup are separate
operations.

## Lint

Checks cover duplicate names, IPs and cables; unresolved endpoints; reused ports;
invalid IPs and VLANs; undefined access VLANs; VLAN mismatches; and cabled shutdown
interfaces. Uncabled devices are informational. A finding may be intentional in
labs that use isolated networks, VRFs, or wireless connections.
