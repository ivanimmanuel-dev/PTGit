# PT Git

**Meaningful version control for Cisco Packet Tracer labs.**

[![Tests](https://github.com/ivanimmanuel-dev/PTGit/actions/workflows/tests.yml/badge.svg)](https://github.com/ivanimmanuel-dev/PTGit/actions/workflows/tests.yml)

See what changed in your network: device configurations, IP addresses, VLANs,
interfaces, and cables. PT Git turns `.pkt` files into readable diffs, locally
and in GitHub pull requests.

**Before**

```text
Binary files a/lab.pkt and b/lab.pkt differ
```

**With PT Git**

```diff
R1
+ interface GigabitEthernet0/1
+  ip address 10.10.20.1/24

SW2
-  switchport access vlan 10
+  switchport access vlan 20

Topology
+ R1:GigabitEthernet0/1 <-> SW2:GigabitEthernet0/1 [eStraightThrough]
```

Excerpt from the [example diff](examples/diff.txt).
[Watch the terminal demo](docs/demo.md) or [read the transcript](docs/demo/demo.txt).

## Quick start

Requires **Python 3.10+** and **Git**. Install from GitHub:

```console
python -m pip install "git+https://github.com/ivanimmanuel-dev/PTGit.git@main"
cd networking-labs
ptgit init
git diff -- lab.pkt
```

Run `ptgit init` in an existing Git repository, then commit `.gitattributes`.
Save a change in Packet Tracer and run `git diff` to see it. Staged changes work
with `git diff --cached`. Each clone needs its own `ptgit init`.

PT Git runs offline with no third-party runtime dependencies. Packet Tracer
doesn't need to be installed to inspect a saved lab.

## Commands

| Command | Purpose |
|---|---|
| `ptgit init` | Enable readable `.pkt` diffs in this Git repository |
| `ptgit diff old.pkt new.pkt` | Compare two saved labs |
| `ptgit show lab.pkt` | Read a lab's configuration and topology |
| `ptgit lint lab.pkt` | Check for common configuration problems |
| `ptgit export lab.pkt --json` | Export a deterministic JSON snapshot |

The default view uses running configuration. Add `--config startup` to inspect
startup configuration instead. Git and the GitHub Action use running configuration.

For scripts, `diff --exit-code` returns **1** when changes exist. `lint` returns
**1** for errors, or for warnings with `--strict`; `lint --json` returns structured
findings. All commands return **2** for input or setup errors and **0** on success.
`python -m ptgit` also works.

## GitHub pull requests

The Action adds a readable diff and lint findings to the workflow's **Job Summary**,
with a JSON report attached as an artifact.

```yaml
name: PT Git
on: [pull_request]
permissions:
  contents: read
jobs:
  packet-tracer-diff:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: ivanimmanuel-dev/PTGit@main
```

GitHub's file view still shows a binary change; open the workflow summary for the
PT Git diff. See [Action options and examples](docs/github-action.md).

## What gets compared

- Device names, models, power state, and saved IOS configuration.
- IP addresses, gateways, DNS, VLANs, and selected hardware-port settings.
- Cable endpoints and cable types.

Layout changes, internal save IDs, runtime counters, and device ordering are
ignored. ACL and route-map command order is preserved.

A clean diff means these supported fields agree. Service data, wireless settings
outside IOS, IoT programs, workspace notes, and simulation events aren't included.
Device renames currently appear as removal/addition. PT Git reads `.pkt` files;
it doesn't edit labs or handle `.pka` activities.

[Comparison rules](docs/semantics.md) · [Git setup details](docs/git-integration.md)

## Tested with Packet Tracer

On **Packet Tracer 9.0.1.0858**, re-saving a 10-device lab produced no semantic
diff despite changed binary bytes. Renaming a router and removing a PC gateway
were detected by the CLI, Git, and the local Action runner. Nine bundled Cisco
samples also passed decoding and inspection checks.

[Validation results](docs/verification.md) list the files and checks performed.
[Help expand coverage](docs/real-lab-validation.md) with your own labs.

## Development

```console
git clone https://github.com/ivanimmanuel-dev/PTGit.git
cd PTGit
python -m pip install -e .
python -m unittest discover -s tests -v
```

The fixtures in `examples/` are small synthetic inputs for tests and demos.
See [Contributing](CONTRIBUTING.md) for packaging and real-lab validation.

## License and credits

MIT. The decoder builds on [Unpacket](https://github.com/Punkcake21/Unpacket)
and [pktforge](https://github.com/Schryzon/pktforge).
[Third-party notices](THIRD_PARTY_NOTICES.md) include their licenses and attribution.

[Changelog](CHANGELOG.md) · [Security](SECURITY.md) ·
[Release notes](docs/release-notes-v0.1.0.md)
