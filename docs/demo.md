# Terminal demo

The demo shows the same lab change three ways: Git's binary diff, `ptgit diff`,
and Git with PT Git enabled.

[Read the transcript](demo/demo.txt), or download and open
[the 12-second replay](demo/index.html) in a browser. The replay runs offline.
GitHub displays the HTML source rather than playing it inline.

## Regenerate

```console
python scripts/demo.py
```

The script captures command output from a temporary Git repository using the
synthetic fixtures in `examples/`. It produces:

- `docs/demo/index.html` — browser replay.
- `docs/demo/demo.cast` — asciinema v2 recording.
- `docs/demo/demo.txt` — plain-text transcript.

With asciinema installed, run `asciinema play docs/demo/demo.cast`.
To make a GIF or video, record the browser replay and crop to the terminal panel.
