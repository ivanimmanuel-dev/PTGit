# Unchanged re-save

**Passed — Packet Tracer 9.0.1.0858, 2026-10-05.**

A contributor opened an existing lab and saved a copy without editing. The build
was confirmed in Help → About.

| Check | Result |
|---|---|
| Binary data | Changed; 86,163 → 86,166 bytes |
| Running and startup models | Identical |
| JSON exports and readable snapshots | Identical in both modes |
| Devices / cables | 10 / 8, unchanged |
| Lint | 0 errors, 0 warnings; 1 uncabled-device notice |
| Ordinary Git | Reports a binary change |
| PT Git, staged and unstaged | Empty diff |
| Original file | Unchanged |

[Hashes and machine-readable results](gui-resave.json) ·
[Subsequent edit comparison](gui-edits.md)

The lab and its decoded configuration are kept outside the repository.
