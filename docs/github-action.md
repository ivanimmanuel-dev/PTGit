# GitHub Action

**PT Git Diff** compares `.pkt` files changed in a pull request. The diff and
lint findings appear in the workflow's Job Summary. `report.json` and
`summary.md` are uploaded as an artifact.

## Setup

Add `.github/workflows/ptgit.yml` to your lab repository:

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

The Action uses Python 3.12 on Ubuntu. A full commit SHA can replace the version
tag. GitHub's Files changed tab still shows binary files; open the Job Summary
to read the comparison.

## Inputs

| Input | Default | Description |
|---|---|---|
| `base`, `head` | Pull request commit IDs | Full commit SHAs available in the checkout |
| `max-files` | `40` | Changed labs to inspect, from 1 to 100 |
| `timeout-seconds` | `30` | Seconds per lab comparison, from 1 to 120 |
| `fail-on-lint` | `false` | Fail when lint reports errors |
| `upload-artifact` | `true` | Upload JSON and summary with 14-day retention |

```yaml
- uses: ivanimmanuel-dev/PTGit@v0.1.0
  id: ptgit
  with:
    fail-on-lint: 'true'
    max-files: '20'
```

Outputs: `report` is the path to `report.json`; `changed-files` is the number of
changed lab paths.

## Reports

Comparison runs from the common ancestor of `base` and `head` to `head`. It
includes added, removed, modified, renamed, and type-changed `.pkt` files.
A filename-only rename can have an empty lab diff. Decode failures fail the
step and appear alongside results for the other files.

JSON includes commit IDs, tool/schema versions, counts, diffs, and lint findings.
Records are sorted. Previews contain up to 80,000 diff characters and 100
findings per lab; totals include findings beyond the preview. Large summaries
direct you to the report artifact.

Artifacts are named `ptgit-report-<job>-<run_attempt>`. Use one invocation per
job. With `upload-artifact: 'false'`, the Job Summary is still written.
Common IOS credentials are masked in both reports; see
[configuration data](../SECURITY.md#configuration-data).

## Local reports

From the source checkout:

```console
python -I scripts/action_entry.py --repo /path/to/labs --base FULL_BASE_SHA --head FULL_HEAD_SHA --output-dir /path/to/report
```
