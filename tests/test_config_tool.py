import sys
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

    def test_sequence_failover_and_rollover(self):
        older = t.decode(t.encode(self.make(0xFFFFFFFE)))
        newest = t.decode(t.encode(self.make(1)))
        self.assertEqual(t.selected(older, newest), (1, newest))
        self.assertEqual(t.selected(older, None), (0, older))
        self.assertEqual(t.selected(None, newest), (1, newest))
        self.assertEqual(t.selected(None, None), (None, None))

    def test_unsupported(self):
        cfg = self.make()
        cfg["host_baud"] = 230400
        self.assertIsNone(t.decode(t.encode(cfg)))
        cfg = self.make()
        cfg["rs232_bits"], cfg["rs232_parity"] = 7, 0
        self.assertIsNone(t.decode(t.encode(cfg)))


if __name__ == "__main__":
    unittest.main()
