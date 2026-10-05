# Third-party notices

## Unpacket

Packet Tracer container decoding uses [Unpacket](https://github.com/Punkcake21/Unpacket)
by Punkcake21, from commit `54cb6d6a9b46c6b4973356258cb8df6ae58b2ec7`.

Files: `pt_crypto.py`, `eax.py`, `ctr.py`, `cmac.py`, and `twofish.py` under
`ptgit/_vendor/unpacket/`. Adaptations cover package-relative imports,
decompression size/stream checks, and truncated inputs.
The MIT license is retained in [unpacket/LICENSE](ptgit/_vendor/unpacket/LICENSE).

`twofish.py` is Bjorn Edstrom's 2007 Python adaptation of Dr Brian Gladman's
implementation. Its original copyright and permission notice is retained in
the file. Twofish was designed by Bruce Schneier and colleagues. An outdated
library recommendation has been removed from the header.

## pktforge

Legacy XOR decoding uses [pktforge](https://github.com/Schryzon/pktforge)
by I Nyoman Widiyasa Jayananda, from commit
`5a29c522e99e7ed18f591430cb25a5b0b6f1df3a`.

`legacy_xor_schedule` in `ptgit/_vendor/pktforge_legacy.py` comes from
`pktcore/crypto/pipeline.py`. Decompression uses the same Qt stream reader as
the modern decoder. The MIT license is retained in
[pktforge-LICENSE](ptgit/_vendor/pktforge-LICENSE).
