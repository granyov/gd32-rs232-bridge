#!/usr/bin/env python3
"""Create/inspect persistent Lazarus SoftW RS232 Flash records (SWD-only).

Does not access a serial port or run OpenOCD itself. All writes are explicit.
"""
import argparse
from pathlib import Path
import struct
import zlib

SLOTS = (0x0800F800, 0x0800FC00)
PAGE_SIZE = 1024
MAGIC = 0x3157524C  # LRW1 in little-endian memory
LAYOUT = 1
RECORD = struct.Struct("<IIIII8BI")
FRAME = {"8N1": (8, 0, 1), "8N2": (8, 0, 2),
         "8E1": (8, 1, 1), "8E2": (8, 1, 2),
         "8O1": (8, 2, 1), "8O2": (8, 2, 2),
         "7E1": (7, 1, 1), "7E2": (7, 1, 2),
         "7O1": (7, 2, 1), "7O2": (7, 2, 2)}
PARITY = {0: "N", 1: "E", 2: "O"}
FLOW = {"none": 0, "rtscts": 1}
FIELDS = ("magic", "layout", "sequence", "host_baud", "rs232_baud",
          "host_bits", "host_parity", "host_stop", "rs232_bits",
          "rs232_parity", "rs232_stop", "flow", "reserved", "crc32")


def crc32(payload):
    return zlib.crc32(payload) & 0xFFFFFFFF


def validate(cfg):
    if cfg is None:
        return False
    if cfg["magic"] != MAGIC or cfg["layout"] != LAYOUT:
        return False
    if cfg["sequence"] in (0, 0xFFFFFFFF) or cfg["reserved"] != 0:
        return False
    if cfg["flow"] not in FLOW.values():
        return False
    if not all(1200 <= cfg[x] <= 115200 for x in ("host_baud", "rs232_baud")):
        return False
    for key in ("host", "rs232"):
        frame = (cfg[f"{key}_bits"], cfg[f"{key}_parity"], cfg[f"{key}_stop"])
        if frame not in FRAME.values():
            return False
    return cfg["crc32"] == crc32(RECORD.pack(*(cfg[f] for f in FIELDS))[:28])


def decode(blob):
    if len(blob) < RECORD.size:
        return None
    cfg = dict(zip(FIELDS, RECORD.unpack_from(blob)))
    return cfg if validate(cfg) else None


def encode(cfg):
    payload = RECORD.pack(*(cfg[f] for f in FIELDS))
    checksum = crc32(payload[:28])
    cfg = dict(cfg, crc32=checksum)
    return RECORD.pack(*(cfg[f] for f in FIELDS))


def selected(a, b):
    if a is None:
        return (1, b) if b is not None else (None, None)
    if b is None:
        return 0, a
    # Same rollover-aware ordering as MCU C code.
    delta = (b["sequence"] - a["sequence"]) & 0xFFFFFFFF
    return (1, b) if 0 < delta < 0x80000000 else (0, a)


def describe(c):
    if c is None:
        return "invalid / empty"
    hf = f'{c["host_bits"]}{PARITY[c["host_parity"]]}{c["host_stop"]}'
    rf = f'{c["rs232_bits"]}{PARITY[c["rs232_parity"]]}{c["rs232_stop"]}'
    return (f'seq={c["sequence"]} host={c["host_baud"]}/{hf} '
            f'RS232={c["rs232_baud"]}/{rf} '
            f'flow={next(k for k, v in FLOW.items() if v == c["flow"])}')


def read_slots(args):
    a = Path(args.slot_a).read_bytes()
    b = Path(args.slot_b).read_bytes()
    if len(a) != PAGE_SIZE or len(b) != PAGE_SIZE:
        raise ValueError("Each SWD slot dump must be exactly 1024 bytes")
    return decode(a), decode(b)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    cmds = parser.add_subparsers(dest="command", required=True)
    for verb in ("show", "prepare"):
        sub = cmds.add_parser(verb)
        sub.add_argument("--slot-a", required=True, type=Path,
                         help="1 KiB SWD dump at 0x0800F800")
        sub.add_argument("--slot-b", required=True, type=Path,
                         help="1 KiB SWD dump at 0x0800FC00")
        if verb == "prepare":
            sub.add_argument("--output", type=Path, required=True)
            sub.add_argument("--factory", action="store_true",
                             help="Reset all parameters to 38400/8N1/no flow")
            sub.add_argument("--host-baud", type=int)
            sub.add_argument("--rs232-baud", type=int)
            sub.add_argument("--host-frame", choices=FRAME)
            sub.add_argument("--rs232-frame", choices=FRAME)
            sub.add_argument("--flow", choices=FLOW)
    args = parser.parse_args()
    a, b = read_slots(args)
    idx, chosen = selected(a, b)
    print("Slot A:", describe(a))
    print("Slot B:", describe(b))
    print("Active:", ("factory defaults" if idx is None else "A" if idx == 0 else "B"))
    if args.command == "show":
        return
    if args.factory or chosen is None:
        values = dict(host_baud=38400, rs232_baud=38400,
                      host_frame="8N1", rs232_frame="8N1", flow="none")
    else:
        values = dict(host_baud=chosen["host_baud"],
                      rs232_baud=chosen["rs232_baud"],
                      host_frame=f'{chosen["host_bits"]}{PARITY[chosen["host_parity"]]}{chosen["host_stop"]}',
                      rs232_frame=f'{chosen["rs232_bits"]}{PARITY[chosen["rs232_parity"]]}{chosen["rs232_stop"]}',
                      flow=next(k for k, v in FLOW.items() if v == chosen["flow"]))
    for k in values:
        opt = getattr(args, k)
        if opt is not None:
            values[k] = opt
    cfg = dict(magic=MAGIC, layout=LAYOUT,
               sequence=1 if chosen is None or chosen["sequence"] == 0xFFFFFFFE
               else chosen["sequence"] + 1,
               host_baud=values["host_baud"], rs232_baud=values["rs232_baud"],
               host_bits=FRAME[values["host_frame"]][0],
               host_parity=FRAME[values["host_frame"]][1],
               host_stop=FRAME[values["host_frame"]][2],
               rs232_bits=FRAME[values["rs232_frame"]][0],
               rs232_parity=FRAME[values["rs232_frame"]][1],
               rs232_stop=FRAME[values["rs232_frame"]][2],
               flow=FLOW[values["flow"]], reserved=0, crc32=0)
    data = encode(cfg)
    if not validate(dict(zip(FIELDS, RECORD.unpack(data)))):
        parser.error("Unsupported parameters: baud must be 1200..115200")
    target_idx = 0 if idx is None else 1 - idx
    target = SLOTS[target_idx]
    # A full sector image is deliberate: the SWD tool must erase only this page.
    if args.output.exists():
        parser.error("Output file exists; refusing to overwrite")
    args.output.write_bytes(data + b"\xFF" * (PAGE_SIZE - len(data)))
    print(f'New configuration: {describe(decode(data))}')
    print(f'Write ONLY inactive slot {"AB"[target_idx]} at 0x{target:08X}')
    print(f'Output: {args.output} ({PAGE_SIZE} bytes)')
    print('Using a suitable OpenOCD target/adapter, HALT the MCU, then:')
    print(f'flash write_image erase {args.output} 0x{target:08X} bin')
    print(f'verify_image {args.output} 0x{target:08X} bin')
    print('reset run')


if __name__ == "__main__":
    main()
