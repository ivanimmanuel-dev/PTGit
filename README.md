# PTGit

Readable Git diffs for Cisco Packet Tracer `.pkt` files. Compare device
configuration, IP addresses, VLANs, and cables from the command line or in a
GitHub pull request.

[![Tests](https://github.com/ivanimmanuel-dev/PTGit/actions/workflows/tests.yml/badge.svg)](https://github.com/ivanimmanuel-dev/PTGit/actions/workflows/tests.yml)

[Download v0.1.0](https://github.com/ivanimmanuel-dev/PTGit/releases/tag/v0.1.0) ·
[GitHub Marketplace](https://github.com/marketplace/actions/pt-git-diff)

```diff
R1
  interface GigabitEthernet0/0
   ip address 192.168.10.1/24
   no shutdown
+ interface GigabitEthernet0/1
+  ip address 10.10.20.1/24
+  no shutdown

SW2
  interface GigabitEthernet0/1
   switchport mode access
-  switchport access vlan 10
+  switchport access vlan 20

Topology
+ R1:GigabitEthernet0/1 <-> SW2:GigabitEthernet0/1 [eStraightThrough]
```

## Install

Requires Python 3.10+ and Git. From your lab's Git repository:

```console
python -m pip install "git+https://github.com/ivanimmanuel-dev/PTGit.git@v0.1.0"
ptgit init
git add .gitattributes
git diff -- lab.pkt
```

Commit `.gitattributes` with your lab. Each collaborator runs `ptgit init` once
to register the converter in their clone. Staged changes work with
`git diff --cached`.

PTGit runs offline and uses the Python standard library. Packet Tracer is only
needed to create or edit the lab.

## Commands

| Command | Purpose |
|---|---|
| `ptgit init` | Set up `.pkt` diffs in the current Git repository |
| `ptgit diff old.pkt new.pkt` | Compare two saves |
| `ptgit show lab.pkt` | Read configuration and topology |
| `ptgit lint lab.pkt` | Check IPs, VLANs, and cable connections |
| `ptgit export lab.pkt --json` | Export lab data as JSON |

The default view uses running configuration. `diff`, `show`, `lint`, and `export`
accept `--config startup`. Git diffs and the Action use running configuration.

For scripts, `diff --exit-code` returns 1 when changes exist. `lint` returns 1
for errors; add `--strict` to include warnings or `--json` for structured findings.
Input and setup errors return 2. Successful commands return 0.

## GitHub Action

Add this workflow to your lab repository. Open its **Job Summary** for the diff;
the JSON report is attached as an artifact.

```yaml
name: PTGit
on: [pull_request]
permissions:
  contents: read
jobs:
  packet-tracer-diff:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: ivanimmanuel-dev/PTGit@v0.1.0
```

[Action options](docs/github-action.md) · [Git setup](docs/git-integration.md)

## Compared fields

PTGit compares device names, types, models, power state, saved IOS configuration,
VLAN databases, host gateways and DNS, port IP settings, and cable endpoints/types.
Layout, internal IDs, runtime counters, and device ordering are ignored.
ACL and route-map command order is preserved.

Device renames appear as removal/addition. `.pka` activities, simulation events,
IoT programs, service records, and wireless settings outside IOS are excluded.
See the [comparison rules](docs/semantics.md) for details.

## Development and license

[Contributing](CONTRIBUTING.md) covers setup and tests.
[Release history](https://github.com/ivanimmanuel-dev/PTGit/releases) lists versions.

MIT licensed. Decoding uses [Unpacket](https://github.com/Punkcake21/Unpacket)
and [pktforge](https://github.com/Schryzon/pktforge).
See [third-party notices](THIRD_PARTY_NOTICES.md) and [security reporting](SECURITY.md).
