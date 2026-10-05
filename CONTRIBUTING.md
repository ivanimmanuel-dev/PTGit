# Contributing

Use Python 3.10+ with Git on your PATH.

```console
python -m pip install -e .
python -m unittest discover -s tests -v
```

For a bug report, include the command, expected result, PTGit/Python versions,
operating system, and Packet Tracer build. A small before/after lab pair helps
reproduce comparison problems.

Include a fixture and expected output when changing comparison behavior.
Preserve command order in ACLs, route maps, and repeated interface contexts.

The XML files in `tests/fixtures/` are test fixtures. Their `.pkt` equivalents can be
regenerated with an [Unpacket](https://github.com/Punkcake21/Unpacket) checkout:

```console
python scripts/build_fixtures.py /path/to/Unpacket
```

To check packaging and a fresh installation:

```console
python -m pip install build twine
python -m build
python -m twine check dist/*
python scripts/check_install.py dist/packet_tracer_git-0.1.0-py3-none-any.whl
```

Keep upstream license notices when changing vendored code. Report vulnerabilities
through [private reporting](https://github.com/ivanimmanuel-dev/PTGit/security/advisories/new).
