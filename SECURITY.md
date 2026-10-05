# Security

## Report a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/ivanimmanuel-dev/PTGit/security/advisories/new).
Include the PT Git version, Python version, operating system, affected command,
and a minimal example or source reference. Remove credentials and private lab data
from attachments. Security fixes target the latest 0.1.x version.

## Lab data and reports

Local diffs and exports include saved configuration, including credentials.
The GitHub Action masks common IOS password, secret, community, and key commands;
other saved values remain visible. Review who can access workflow summaries and
artifacts before using the Action with private labs.

Use the Action on ordinary hosted runners with `contents: read` and
`pull_request`, as shown in the [setup guide](docs/github-action.md). Pin the
Action to a reviewed commit for reproducible runs. Avoid `pull_request_target`
and runners that hold unrelated secrets.

## Input limits

PT Git checks modern-container authentication tags, compressed stream lengths,
and XML structure. DTDs and entities are rejected. Inspection reads local files
without modifying them or accessing the network.

| Resource | Limit |
|---|---:|
| Input file | 16 MiB |
| Decoded XML | 64 MiB |
| XML depth / element count | 128 / 250,000 |
| Modeled scalar / device name | 65,536 / 256 characters |
| Devices / links | 4,096 / 16,384 |
| Configuration lines | 50,000 |
| Expanded model, including object overhead | 8 MiB |

Large diffs use bounded alignment. Action comparisons run in a separate process
with a timeout and, on Linux where available, a 768 MiB address-space limit.
The local CLI has no process-level time or memory limit. These controls do not
provide an OS sandbox; decoding large files in pure Python can be slow.

Legacy containers and raw XML are also accepted. A valid container tag verifies
the file's integrity, not its author.
