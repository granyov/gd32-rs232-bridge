import sys
import tempfile
import subprocess
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import uvon_rs232_config as t


class ConfigToolTest(unittest.TestCase):
    def make(self, sequence=1):
        cfg = dict(magic=t.MAGIC, layout=t.LAYOUT, sequence=sequence,
                   host_baud=38400, rs232_baud=9600,
                   host_bits=8, host_parity=0, host_stop=1,
                   rs232_bits=7, rs232_parity=1, rs232_stop=1,
                   flow=1, reserved=0, crc32=0)
        return cfg

    def test_valid_and_corrupt(self):
        blob = t.encode(self.make())
        self.assertEqual(len(blob), 32)
        self.assertEqual(t.decode(blob)["rs232_baud"], 9600)
        altered = bytearray(blob)
        altered[12] ^= 0x01
        self.assertIsNone(t.decode(altered))
        self.assertIsNone(t.decode(b"\xff" * 1024))

    def test_c_firmware_binary_format(self):
        # Shared byte-for-byte with tests/test_config.c, independent runtimes.
        cfg = self.make()
        cfg["rs232_baud"] = 19200
        cfg["rs232_stop"] = 2
        self.assertEqual(t.encode(cfg).hex(), "4c525731010000000100000000960000004b00000800010701020100b049cf0d")

    def test_sequence_failover_and_rollover(self):
        older = t.decode(t.encode(self.make(0xFFFFFFFE)))
        newest = t.decode(t.encode(self.make(1)))
        self.assertEqual(t.selected(older, newest), (1, newest))
        self.assertEqual(t.selected(older, None), (0, older))
        self.assertEqual(t.selected(None, newest), (1, newest))
        self.assertEqual(t.selected(None, None), (None, None))

    def test_verify_cli_readback(self):
        with tempfile.TemporaryDirectory() as root:
            expected = Path(root) / "expected.bin"
            readback = Path(root) / "readback.bin"
            config = t.encode(self.make())
            expected.write_bytes(config + b"\xff" * (t.PAGE_SIZE - len(config)))
            readback.write_bytes(expected.read_bytes())
            command = [sys.executable, str(Path(t.__file__)), "verify",
                       "--expected", str(expected), "--readback", str(readback)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PASS", result.stdout)
            damaged = bytearray(readback.read_bytes())
            damaged[200] = 0
            readback.write_bytes(damaged)
            rejected = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)

    def test_unsupported(self):
        cfg = self.make()
        cfg["host_baud"] = 230400
        self.assertIsNone(t.decode(t.encode(cfg)))
        cfg = self.make()
        cfg["rs232_bits"], cfg["rs232_parity"] = 7, 0
        self.assertIsNone(t.decode(t.encode(cfg)))


if __name__ == "__main__":
    unittest.main()
