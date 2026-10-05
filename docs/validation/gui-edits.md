# Router rename and PC gateway removal

**Detected — Packet Tracer 9.0.1.0858, 2026-10-05.**

The contributor renamed a router and made one additional edit without describing
it in advance. PT Git detected the rename and removal of a PC default gateway.
Decoded XML inspection confirmed the gateway values had been removed.

| Check | Result |
|---|---|
| Binary size | 86,166 → 86,283 bytes |
| Running and startup views | Both show the two changes |
| Other supported fields | Equal after accounting for the changes |
| Devices / physical cables | 10 / 8, unchanged |
| Lint | 0 errors, 0 warnings; 1 uncabled-device notice |
| Installed CLI | Diff returned exit code 1 in both modes |
| Repeated JSON export | Identical output |
| Installed Git, staged and unstaged | Both changes visible |
| Local Action runner | Both changes visible from actual Git commits |
| Original file | Unchanged |

The display-name change appears as one device removed and one added, with three
cable endpoints relabeled. No physical cables were added or removed. The PC's
gateway removal appears at both device and port level.

These edits affect fields shared by the running and startup views; a deliberate
IOS running/startup divergence remains a separate test case.

[Hashes and machine-readable results](gui-edits.json) ·
[Full validation matrix](../real-lab-validation.md)

The lab and its decoded configuration are kept outside the repository.
