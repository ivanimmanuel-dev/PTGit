# Git integration

From a Git repository, enable PTGit and commit the file attributes:

```console
ptgit init
git add .gitattributes
git commit -m "Enable Packet Tracer diffs"
```

You can also pass a repository path: `ptgit init /path/to/labs`.
Setup adds `*.pkt` and `*.PKT` rules and registers a local textconv driver.
Existing attributes and other diff drivers are preserved.

After saving a lab:

```console
git diff -- lab.pkt
git add lab.pkt
git diff --cached -- lab.pkt
```

Git stores the original `.pkt` bytes. Textconv produces the readable review;
its output is not a text patch for editing the binary file.

## Clones and Python changes

Each clone needs `ptgit init`. The driver points to the installed Python and
converter, so refresh it after moving either:

```console
ptgit init --force
```

Paths with spaces are supported. Setup changes repository-local Git settings.

## Troubleshooting

Check which attributes apply to a lab:

```console
git check-attr diff text -- lab.pkt
```

Nested `.gitattributes` files can override the repository rules. An existing
`diff.ptgit.textconv` requires `--force` to replace. An external
`diff.ptgit.command` overrides textconv; remove that setting at its original
scope before running setup.

GitHub does not run textconv. Use the [Action](github-action.md) for pull requests.
