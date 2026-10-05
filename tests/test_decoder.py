import struct
import unittest
import zlib

from ptgit._vendor.unpacket.pt_crypto import uncompress_qt


class DecoderBoundaryTests(unittest.TestCase):
    def test_exact_stream_is_accepted(self):
        payload = b"<PACKETTRACER5/>"
        self.assertEqual(uncompress_qt(struct.pack(">I", len(payload)) + zlib.compress(payload)), payload)

    def test_size_mismatch_truncation_and_trailing_data_are_rejected(self):
        payload = b"<PACKETTRACER5/>"
        stream = zlib.compress(payload)
        cases = [b"", b"abc", struct.pack(">I", len(payload)-1) + stream,
                 struct.pack(">I", len(payload)+1) + stream,
                 struct.pack(">I", len(payload)) + stream[:-1],
                 struct.pack(">I", len(payload)) + stream + b"extra"]
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ValueError):
                uncompress_qt(data)

    def test_declared_output_limit_is_rejected_before_decompression(self):
        with self.assertRaisesRegex(ValueError, "64 MiB"):
            uncompress_qt(struct.pack(">I", 64 * 1024 * 1024 + 1) + zlib.compress(b"a"))
