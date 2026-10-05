# Third-party notices

PT Git reuses **Unpacket** by Punkcake21, under the MIT license. Its full license
is included at `ptgit/_vendor/unpacket/LICENSE` and in built distributions.

- Source: https://github.com/Punkcake21/Unpacket
- Pinned commit: `54cb6d6a9b46c6b4973356258cb8df6ae58b2ec7`
- Copied files: `Decipher/{pt_crypto,eax,ctr,cmac,twofish}.py`
- Changes: package-relative imports; bounded decompression with exact length and
  stream-completion checks; a minimum input length check.

**Twofish implementation attribution:** `twofish.py` is Bjorn Edstrom's Python
adaptation (13 December 2007) of Dr Brian Gladman's implementation. It carries
its own permission notice requiring acknowledgment and retention of the notice.
That original header remains intact. The repository-level MIT license does not
replace the embedded notice. Twofish was designed by Bruce Schneier and colleagues.

The upstream encoder is used only by the development fixture-generation script
from an explicitly supplied upstream checkout; it is not shipped as a PT Git
command or copied into this distribution.

**pktforge** by I Nyoman Widiyasa Jayananda is reused for the small legacy XOR
wrapper, from `pktcore/crypto/pipeline.py`, pinned at
`5a29c522e99e7ed18f591430cb25a5b0b6f1df3a`.
Source: https://github.com/Schryzon/pktforge
The MIT license is included at `ptgit/_vendor/pktforge-LICENSE`.
`legacy_xor_schedule` is copied verbatim; `try_legacy_decompile` delegates to the
bounded Qt reader instead of trying raw/gzip decompression. The native build
bridge and its auto-compilation behavior are not included.

packet-tracer-skill was evaluated as an alternative and schema reference; no code
was copied. Cisco sample files used for validation are not redistributed.
PT Git is independent and unaffiliated with Cisco.
