# GitHub Action

PT Git compares changed `.pkt` files in a pull request and writes the diff to the
workflow's Job Summary. It also uploads `report.json` and `summary.md` as an artifact.

## Setup

Add `.github/workflows/ptgit.yml` to your lab repository:

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

The Action uses Python 3.12 on Ubuntu. Replace `main` with a reviewed full commit
SHA to pin a version. Fork pull requests work with read-only permissions.

Open the workflow run's summary to read the diff. GitHub's Files changed tab
continues to show the original binary files.

## Options

| Input | Default | Meaning |
|---|---|---|
| `base`, `head` | Pull request commit IDs | Full commit SHAs available in the checkout |
| `max-files` | `40` | Maximum changed labs to inspect, from 1 to 100 |
| `timeout-seconds` | `30` | Comparison timeout per lab pair, from 1 to 120 seconds |
| `fail-on-lint` | `false` | Fail the step when lint finds errors |
| `upload-artifact` | `true` | Upload JSON and summary with 14-day retention |

Outputs are `report`, the JSON report path, and `changed-files`, the number of
changed lab paths. For example:

```yaml
- uses: ivanimmanuel-dev/PTGit@main
  id: ptgit
  with:
    fail-on-lint: 'true'
    max-files: '20'
```

## Report behavior

Comparison uses the common ancestor of `base` and `head`, through `head`. Added,
removed, modified, renamed, and type-changed `.pkt` paths are included. File
extensions are matched case-insensitively. A filename-only rename can produce
an empty semantic diff.

Each lab gets device/link counts, a diff, and lint findings. Decode failures fail
the step while preserving the other file reports. A run with no changed labs
succeeds.

Reports use the same comparison code as the CLI and are deterministic for the
same inputs and options. The JSON includes commit IDs, tool and schema versions,
and sorted file records. Previews include up to 80,000 diff characters and 100
findings per lab; truncation is marked and counts remain complete. Summaries
above 900,000 bytes direct users to the artifact.

The artifact is named `ptgit-report-<job>-<run_attempt>`. Use one Action invocation
per job to avoid artifact-name collisions.

Common IOS credentials are masked in both outputs; other saved values remain.
Disabling artifact upload leaves the Job Summary enabled. See [Security](../SECURITY.md)
for report visibility and runner guidance.

## Run locally

From the PT Git source checkout:

```console
python -I scripts/action_entry.py --repo /path/to/labs --base FULL_BASE_SHA --head FULL_HEAD_SHA --output-dir /path/to/report
```

This writes the two report files locally. The runner requires the source checkout,
including its worker script. CI also runs the composite Action against two fixture
commits and checks the resulting report.
