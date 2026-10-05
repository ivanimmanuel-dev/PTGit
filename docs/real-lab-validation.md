# Test with your Packet Tracer labs

This guide creates before/after pairs for configuration and topology changes.
Use a new lab in Packet Tracer and save each case separately. The synthetic
`examples/*.pkt` files are decoder fixtures, not complete labs for the GUI.

The current results cover an unchanged re-save, a display-name change, and a PC
gateway removal on **9.0.1.0858**. The full matrix below is still open;
see [recorded results](verification.md).

## Make the baseline once

1. Open Packet Tracer. Copy the exact version/build from **Help → About** into
   `packet_tracer_build` in a copy of `validation-manifest.example.json`. Place
   that manifest alongside your saved lab pairs. Record OS in a `notes` field.
2. Place a 2911 router and a 2960 switch. Set their display names and IOS hostnames
   to R1 and SW1. Attach R1 GigabitEthernet0/0 to SW1 GigabitEthernet0/1 with a
   copper straight-through cable. Wait for startup/configuration activity to settle.
3. On R1, enter `enable`, `configure terminal`, `hostname R1`,
   `interface GigabitEthernet0/0`, `ip address 192.168.10.1 255.255.255.0`,
   `no shutdown`, `exit`, `end`, then `copy running-config startup-config`.
4. On SW1, enter configuration mode, set `hostname SW1`, create `vlan 10` and
   `vlan 20`, then on `interface GigabitEthernet0/1` set `switchport mode access`,
   `switchport access vlan 10`, `no shutdown`. End and copy running to startup.
5. Save as `baseline.pkt`, close it and reopen it. Keep this original unchanged.
   Use a fresh copy opened from baseline for each case below; save with **Save As**.
   Record any incidental changes or unsupported commands alongside the result.

## Produce the pairs

CLI commands below assume you have entered `enable` and `configure terminal`.
Use `end` afterward. Save the `.pkt` file after every change. Except where stated,
do not copy running config to startup, so startup remains a useful control.

| Case / output file | Change from baseline | Expected running diff |
|---|---|---|
| `resaved.pkt` | Open baseline and Save As, with no intentional edit | None; investigate any modeled difference |
| `hostname.pkt` | R1: `hostname EdgeR1` | Hostname/name change; GUI may also synchronize the display name |
| `ipv4.pkt` | R1 G0/0: `ip address 192.168.10.2 255.255.255.0` | Address change |
| `mask.pkt` | R1 G0/0: `ip address 192.168.10.1 255.255.255.128` | Prefix /24 to /25 |
| `shutdown.pkt` | R1 G0/0: `shutdown` | Administrative-state command change |
| `cable-added.pkt` | Add R1 G0/1 ↔ SW1 G0/2 straight-through cable | One link added |
| `cable-removed.pkt` | Delete the original G0/0 ↔ G0/1 cable | One link removed |
| `access-vlan.pkt` | SW1 G0/1: `switchport access vlan 20` | Access VLAN 10 to 20 |
| `vlan-added.pkt` | SW1: `vlan 30`, `name TEST30` | VLAN/config entry added |
| `route.pkt` | R1: `ip route 203.0.113.0 255.255.255.0 192.168.10.254` | Static route added |
| `dhcp.pkt` | R1: `ip dhcp pool TEST`, `network 192.168.10.0 255.255.255.0`, `default-router 192.168.10.1` | DHCP pool lines added |
| `acl.pkt` | R1: `access-list 10 permit 192.168.10.0 0.0.0.255`, then `access-list 10 deny any` | Ordered ACL lines added |
| `renamed.pkt` | Change R1's display name to Edge in the device Config tab | Device removed/added; note any synchronized hostname change |
| `device-added.pkt` | Add an uncabled PC, display name PC2 | One device added |
| `running-only.pkt` | R1 G0/0: `description RUNNING_ONLY`; **do not copy to startup** | Running changes; startup comparison stays clean |

Also open `shutdown.pkt`, enter `no shutdown`, and save `no-shutdown.pkt`. Open
`vlan-added.pkt`, remove VLAN 30 and save `vlan-removed.pkt`. Open
`device-added.pkt`, remove PC2 and save `device-removed.pkt`. These exercise actual
GUI removal paths rather than merely reversing a diff.

Finally open `running-only.pkt`, run `copy running-config startup-config`, accept
the destination prompt, and save `startup-saved.pkt`. Its startup comparison
against `running-only.pkt` must detect the copied description. A `.pkt` file save
and IOS `copy running-config startup-config` are different operations.

## Run and interpret

From the PT Git source tree:

```console
python scripts/validate_real_labs.py /path/to/validation-manifest.json --output /path/to/validation-results.json
```

The report records the build from your manifest, both file hashes, saved metadata,
counts, and pass/fail for each comparison. Inspect the diffs as well:

```console
python -m ptgit diff /path/to/baseline.pkt /path/to/resaved.pkt --exit-code
python -m ptgit diff /path/to/running-only.pkt /path/to/startup-saved.pkt --config startup
```

Keep the original files and hashes. Share the result JSON and sanitized diffs,
plus lab files you have permission to distribute. If an unchanged re-save produces
a diff, include that pair and the unexpected output in a bug report.
