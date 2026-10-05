# Release checklist

The Python distribution is `packet-tracer-git`; the command is `ptgit`.
The unrelated `ptgit` package on PyPI is not this project.

## Prepare

1. Update the version in `pyproject.toml` and `ptgit/__init__.py`, the install-check
   paths, and version assertions in tests.
2. Update the changelog and release notes. Record new Packet Tracer validation
   results in [verification](verification.md).
3. Run the checks below and wait for the Windows/Linux CI matrix and Action
   self-test to pass on the release commit.

```console
python -m unittest discover -s tests -v
python -m pip install build twine
python -m build
python -m twine check dist/*
python scripts/check_install.py dist/packet_tracer_git-0.1.0-py3-none-any.whl
python scripts/demo.py
```

## GitHub release

Tag the checked commit as `v0.1.0` and push the tag. The release workflow runs the
tests, builds wheel and source distributions, and uploads them as workflow
artifacts. Create the GitHub release with those files, SHA-256 checksums, and
[release notes](release-notes-v0.1.0.md).

The tag workflow builds packages without uploading to PyPI. The Action can be
referenced by the same version tag or full commit SHA.

## PyPI setup

Before the first upload, register a Trusted Publisher for `packet-tracer-git`:

| Setting | Value |
|---|---|
| Owner | `ivanimmanuel-dev` |
| Repository | `PTGit` |
| Workflow | `release.yml` |
| Environment | `pypi` |

Create the GitHub `pypi` environment with required reviewers and restrict it to
release tags. Follow the [PyPI setup guide](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).

Dispatch `release.yml` on the version tag with `publish` enabled, then approve the
environment deployment. The publish job downloads the checked build and uses OIDC
to upload it; no API token is stored in the repository.

After uploading, verify `python -m pip install packet-tracer-git` in a fresh
environment and update the README installation command.
