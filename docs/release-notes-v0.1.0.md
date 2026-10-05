# PT Git v0.1.0

PT Git brings readable Git diffs to Cisco Packet Tracer labs.

- Compare saved IOS configuration, IP addresses, VLANs, devices, and cables.
- Use normal `git diff` and `git diff --cached` with `.pkt` files.
- Inspect labs with `show`, check them with `lint`, and export deterministic JSON.
- Read Packet Tracer changes in GitHub workflow summaries with the bundled Action.
- Select running or startup configuration from the CLI.

Requires Python 3.10+. The runtime uses the standard library; modern and legacy
decoding come from Unpacket and pktforge.

## Install

```console
python -m pip install "git+https://github.com/ivanimmanuel-dev/PTGit.git@main"
cd networking-labs
ptgit init
```

## Coverage

Packet Tracer **9.0.1.0858** was used to check an unchanged re-save, a router rename,
and a PC gateway removal. Nine installed Cisco samples also passed inspection.
See [validation results](verification.md) for the recorded checks.

This first version compares selected configuration and topology fields. Renames
appear as removal/addition. Service data, wireless settings outside IOS, IoT
programs, simulation, and `.pka` activities are outside the model.
