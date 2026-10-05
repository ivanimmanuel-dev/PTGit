# Security

Report vulnerabilities through
[GitHub private reporting](https://github.com/ivanimmanuel-dev/PTGit/security/advisories/new).
Include the affected version, command, and a minimal example.

## Configuration data

Local diffs and JSON exports contain saved configuration, including credentials.
The Action masks common IOS password, secret, community, and key commands in
its summary and JSON report. Other saved values remain visible to people with
access to the workflow. Remove credentials before sharing lab files or reports.
