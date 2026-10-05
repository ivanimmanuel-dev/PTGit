# Validation results

Recorded on 2026-10-05 for PT Git 0.1.0.

## Automated checks

| Environment or check | Result |
|---|---|
| Windows, Python 3.14.6, Git for Windows | 59 tests passed |
| Ubuntu under WSL, Python 3.14.4, Git 2.53.0 | 59 tests passed |
| Fresh wheel installation on both systems | CLI and module entry points passed outside the source tree |
| Git integration | Staged/unstaged diffs, paths with spaces, relocation, reinstall, existing attributes and drivers passed |
| Packaging | Wheel and source distribution built; metadata and license checks passed |
| Local Action runner | Compared actual commits and produced deterministic JSON and summaries |

The [CI workflow](https://github.com/ivanimmanuel-dev/PTGit/actions/workflows/tests.yml)
runs Python 3.10–3.14 on Windows and Ubuntu, plus the composite Action self-test.
Each matrix job builds and installs the package before exercising Git integration.

Tests also cover ordering, duplicate identities, malformed containers, XML limits,
resource budgets, credential masking, and isolated Action imports.

## Packet Tracer 9.0.1.0858

One contributor lab with **10 devices and 8 cables** was tested in the application.
The exact build was read from Help → About.

| Change | Result |
|---|---|
| Open and re-save without editing | Binary bytes changed; running/startup models and JSON stayed identical; staged/unstaged Git diffs were empty |
| Rename a router and remove a PC gateway | Both changes appeared in the CLI, installed Git diffs, and local Action report |

[Re-save results](validation/gui-resave.md) ·
[Edit results](validation/gui-edits.md)

The broader [configuration test matrix](real-lab-validation.md) remains open,
including deliberate differences between running and startup IOS configuration.

## Installed Cisco samples

Nine samples from the Packet Tracer 9.0.1 installation passed decoding,
extraction, rendering, and static lint. All cable endpoints resolved.
The versions below are metadata saved in those files; the application builds
that originally wrote them were not tested interactively.

| Sample under `saves/01 Networking/` | Saved version | Devices | Cables |
|---|---|---:|---:|
| `FTP/FTP.pkt` | 5.3.0.0011 | 5 | 4 |
| `NTP/ntp_switch.pkt` | 7.2.0.0000 | 3 | 1 |
| `NAT/Outside_Nat.pkt` | 5.2.0.0068 | 3 | 2 |
| `OSPF/ospf_network_lo_p2p.pkt` | 6.1.0.0026 | 2 | 1 |
| `DHCP/dhcpv6_router_as_client.pkt` | 6.1.0.0026 | 2 | 1 |
| `IPv6/Ipv6Ip Tunneling/ipv6ip_ospf.pkt` | 6.0.0.0002 | 3 | 2 |
| `Wireless/Wireless LAN/WLC/wlc_pt_simple_wlan_wep_authen.pkt` | 7.1.0.0000 | 7 | 3 |
| `Wireless/5G/5G.pkt` | 9.0.0.0000 | 5 | 0 |
| `REP/rep_two_devices.pkt` | 8.2.1.0000 | 5 | 3 |

`Outside_Nat.pkt` exercises the legacy decoder; the other samples use the modern
path. [Sample hashes and counts](validation/sample-smoke-results.json) are included.
The Cisco samples and contributor lab are not redistributed.

## Reproduce

```console
python -m unittest discover -s tests -v
python scripts/check_install.py /path/to/packet_tracer_git-0.1.0-py3-none-any.whl
python scripts/verify_samples.py /path/to/samples --limit 20
```

For controlled changes in Packet Tracer, follow the
[lab validation guide](real-lab-validation.md). The [comparison rules](semantics.md)
define which fields each check covers.
