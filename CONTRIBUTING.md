# Contributing

PT Git uses Python 3.10+ and the standard library. Git must be on your PATH for
the integration tests.

```console
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Changes and tests

Open a pull request with the behavior you're changing and how you tested it.
For comparison changes, include a small fixture and the expected diff. Preserve
command order where it affects configuration, especially ACLs, route maps, and
repeated interface blocks.

Real `.pkt` samples are particularly useful. Follow the
[Packet Tracer validation guide](docs/real-lab-validation.md) to produce before/after
pairs and record the exact application build. Share a minimal lab you own, with
credentials and private course material removed.

The tests cover the decoder, normalization, lint, CLI, Git textconv, and Action
reports. Integration tests use temporary repositories. The examples are synthetic
decoder fixtures; create real labs in Packet Tracer for compatibility testing.

## Build and install

```console
python -m pip install build twine
python -m build
python -m twine check dist/*
python scripts/check_install.py dist/packet_tracer_git-0.1.0-py3-none-any.whl
```

The install check creates a fresh environment, exercises the CLI outside the
source tree, and checks staged and unstaged Git diffs.

Keep upstream license headers when editing vendored code, and document changes
in [third-party notices](THIRD_PARTY_NOTICES.md). Report security issues through
the [private reporting channel](SECURITY.md).

Maintainers: [release checklist](docs/publishing.md).
