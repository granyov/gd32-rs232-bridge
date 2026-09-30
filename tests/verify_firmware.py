#!/usr/bin/env python3
"""Verify vectors, memory bounds and matching HEX/BIN for a linked ELF."""
import argparse
from pathlib import Path
import struct
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('elf', type=Path)
parser.add_argument('--prefix', default='arm-none-eabi-')
parser.add_argument('--hse', type=int, default=16000000)
parser.add_argument('--host-baud', type=int, default=38400)
parser.add_argument('--logger-baud', type=int, default=38400)
args = parser.parse_args()
elf = args.elf
symbols = {}
for line in subprocess.check_output([args.prefix+'nm', '-n', str(elf)], text=True).splitlines():
    parts = line.split()
    if len(parts) == 3:
        symbols[parts[2]] = int(parts[0], 16)

binary = elf.with_suffix('.bin').read_bytes()
memory = {}
base = 0
eof = False
for line in elf.with_suffix('.hex').read_text().splitlines():
    assert not eof, 'Data after EOF record'
    assert line.startswith(':')
    record = bytes.fromhex(line[1:])
    assert len(record) == record[0]+5 and sum(record) % 256 == 0
    addr = int.from_bytes(record[1:3], 'big')
    kind = record[3]
    data = record[4:-1]
    if kind == 0:
        for i, value in enumerate(data):
            location = base + addr + i
            assert location not in memory
            memory[location] = value
    elif kind == 4:
        base = int.from_bytes(data, 'big') << 16
    elif kind == 1:
        eof = True
    elif kind == 5:
        assert int.from_bytes(data, 'big') == (symbols['Reset_Handler'] | 1)
    else:
        raise AssertionError('Unsupported HEX record type: '+str(kind))
assert eof
assert min(memory) == 0x08000000
assert max(memory) < 0x08010000
assert len(binary) == max(memory)-min(memory)+1
assert all(binary[addr-0x08000000] == value for addr, value in memory.items())
assert struct.unpack_from('<I', binary, 0)[0] == 0x20005000
for index, name in [(1, 'Reset_Handler'), (15, 'SysTick_Handler'),
                    (16+37, 'USART0_IRQHandler'), (16+38, 'USART1_IRQHandler')]:
    entry = struct.unpack_from('<I', binary, index*4)[0]
    assert entry == (symbols[name] | 1), (name, hex(entry))
    assert 0x08000000 <= (entry & ~1) < 0x08010000
    assert symbols[name] != symbols['Default_Handler']
for legacy in ('sw_usart_process_rx', 'sw_usart_process_tx',
               'HAL_TIM_PeriodElapsedCallback', 'HAL_UART_IRQHandler'):
    assert legacy not in symbols, legacy
assert 0x20000000 <= symbols['_ebss'] < 0x20005000
assert symbols['_ebss'] + 0x600 <= symbols['_estack']
assert b'lazarus-gd32-rs232-1.1.0' in binary
assert ('HSE%dMHz' % (args.hse // 1000000)).encode() in binary
assert ('host=%dU logger=%dU 8N1' % (args.host_baud, args.logger_baud)).encode() in binary
print('PASS:', elf.name)
print('  BIN/HEX match; Intel HEX checksums valid; flash origin 0x08000000')
print('  Reset, SysTick, USART0 and USART1 vectors resolve to real handlers')
print('  No HDLC bit-banging or HAL RX interrupt state machine linked')
print('  Image bytes:', len(binary), 'RAM .data+.bss:', symbols['_ebss']-0x20000000)
