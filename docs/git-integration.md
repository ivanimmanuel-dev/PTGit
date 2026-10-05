# Git integration

Run `ptgit init` in a Git repository, or pass its path:

```console
ptgit init /path/to/networking-labs
```

From that repository, commit the generated attributes:

```console
git add .gitattributes
git commit -m "Enable Packet Tracer diffs"
```

PT Git adds rules for `*.pkt` and `*.PKT` to `.gitattributes` and installs a local
textconv driver. Existing attributes and unrelated drivers are preserved. Global
Git configuration is unchanged.

After editing and saving a lab:

```console
git diff -- lab.pkt
git add lab.pkt
git diff --cached -- lab.pkt
```

`ptgit textconv` also accepts the extensionless temporary files Git creates.
Git stores the original binary bytes; the readable diff is for review and cannot
be applied as a text patch.

## Clones and installation changes

Commit `.gitattributes` so Git knows which files use PT Git. Each collaborator
then runs `ptgit init` to register their installed converter.

The driver stores absolute Python and converter paths. After moving the source
tree or changing Python installations, refresh it:

```console
ptgit init --force
```

Repeating setup is safe. Paths containing spaces are supported. Textconv output
is not cached in Git notes.

## Existing Git settings

The PT Git attribute block is appended after existing rules. Nested
`.gitattributes` files can still override it. Inspect the effective driver with:

```console
git check-attr diff text -- lab.pkt
```

A different `diff.ptgit.textconv` requires `--force` to replace. An external
`diff.ptgit.command` takes precedence over textconv, so setup reports the conflict.
Remove that setting at the scope where it was configured, then rerun setup.

GitHub does not run local textconv. Use the [GitHub Action](github-action.md) to
show these diffs in pull requests.
