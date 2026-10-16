#!/usr/bin/env python3
"""Build self-contained website firmware ZIP packages without extra modules.

Usage: make all verify && python3 tools/package_website.py
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "firmware"
DEFAULT_BUILD = ROOT / "build/hse16000000-host38400-logger38400"

NOTICE_STABLE = """LAZARUS UVON | Lazarus SoftW RS232
===================================

ОФИЦИАЛЬНЫЙ ОПУБЛИКОВАННЫЙ ОБРАЗ — v1.1.0 (STABLE)

Назначение: прошивка контроллеров GD32F103C8T6 портов V.24 в
режиме RS-232 для промышленного компьютера LAZARUS UVON.

Статус проверки: 30.09.2026 подтвержден обмен с ACE ADL-200A через
/dev/ttyS5 при 38400 бод, 8N1. Другой порт, иные скорости, длительная
нагрузка и полноценная проверка после чтения Flash НЕ подтверждены.

Параметры: входной UART 38400 / 8N1, внешний RS-232 38400 / 8N1,
RTS/DTR активны постоянно, flow control нет.
MCU GD32F103C8T6, HXTAL 16 МГц.
BIN нужно записывать с адреса 0x08000000. HEX содержит адреса.

ВАЖНО: перед записью сохраните все 64 КиБ Flash, option bytes и
проверьте подключение SWD (XP6/XP8). Не отключайте защиту чтения
автоматически: это может стереть предыдущую прошивку.
Не записывайте образ в RK3568 либо подключенный измеритель.

Этот пакет содержит ИСХОДНЫЕ проверенные бинарники v1.1.0 без
изменения содержимого; новое название относится к ZIP и документам.
Функции конфигурации версии 1.2.0 ЗДЕСЬ ОТСУТСТВУЮТ.

Документация:
https://github.com/granyov/gd32-rs232-bridge/blob/main/docs/BOARD_AND_FLASHING.md
"""

NOTICE_RELEASE = """LAZARUS UVON | Lazarus SoftW RS232
===================================

РАБОЧАЯ ПРОГРАММНАЯ СБОРКА v1.2.0

Назначение: прошивка GD32F103C8T6 портов V.24 / RS-232
промышленного компьютера LAZARUS UVON.

ПРОВЕРЕНО: кросс-компиляция для Cortex-M3, программные тесты
очередей, CRC32, двух слотов, RTS/CTS, HEX/BIN и границы памяти.
НЕ ПРОВЕРЕНО: работа v1.2.0 на физических платах УВОН.
Аппаратно подтверждена только предыдущая версия v1.1.0.

Возможности: независимые скорости UART хоста и внешнего RS-232
1200..115200 бод, режимы 8N1/N2, 8E1/E2, 8O1/O2, 7E1/E2,
7O1/O2, программное RTS/CTS на внешней линии, настройки Flash.

Заводские значения: 38400 / 38400, 8N1, flow control выключен.
Конфигурацию нужно записывать через SWD, после этого сделать reset.
Через обычный UART параметры не меняются.
При использовании RTS/CTS необходимо подтвердить подключение
и полярность сигналов CTS/RTS на конкретной плате.

Запись BIN: адрес 0x08000000. HEX содержит адреса.
ВНИМАНИЕ: страницы конфигурации 0x0800F800 (A) и 0x0800FC00 (B)
не должны стираться при обновлении программы. Mass erase уничтожит
их содержимое. До записи сохраните все 64 КиБ Flash и option bytes.
Нельзя автоматически отключать защиту чтения: возможна потеря данных.

Подробная инструкция: CONFIGURATION.md, BOARD_AND_FLASHING.md
Документация и релиз:
https://github.com/granyov/gd32-rs232-bridge/releases/tag/v1.2.0
"""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git_commit():
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def package_zip(output, filename, files, info):
    output.mkdir(parents=True, exist_ok=True)
    items = {}
    for name, data in files.items():
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError("Unsafe name " + name)
        items[name] = data if isinstance(data, bytes) else data.encode("utf-8")

    hashes = "".join(
        f"{sha256(data)}  {name}\n"
        for name, data in sorted(items.items())
        if name.startswith("firmware/")
    )
    if not hashes:
        raise RuntimeError("No firmware images in package")
    items["SHA256SUMS.txt"] = hashes.encode("ascii")
    items["BUILD_INFO.json"] = json.dumps(
        info, ensure_ascii=False, indent=2, sort_keys=True
    ).encode("utf-8") + b"\n"
    target = output / filename
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(items.items()):
            metadata = zipfile.ZipInfo(name, date_time=(2026, 10, 16, 0, 0, 0))
            metadata.compress_type = zipfile.ZIP_DEFLATED
            metadata.external_attr = 0o644 << 16
            z.writestr(metadata, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        names = set(z.namelist())
        assert "SHA256SUMS.txt" in names and "README_RU.txt" in names
        for row in hashes.splitlines():
            digest, _, rel = row.partition("  ")
            assert digest == sha256(z.read(rel)), rel
    return target


def build_stable(out):
    stem = "lazarus-gd32-rs232-hse16000000-38400-38400"
    files = {
        "firmware/" + stem + suffix: (FIRMWARE / (stem + suffix)).read_bytes()
        for suffix in (".bin", ".hex")
    }
    # Strict match against previously published immutable checksums.
    expected = {}
    for line in (FIRMWARE / "SHA256SUMS").read_text().splitlines():
        h, path = line.split(None, 1)
        expected[path.strip()] = h
    for name, data in files.items():
        original = name.removeprefix("firmware/")
        assert sha256(data) == expected[original], original
    assert len(files["firmware/" + stem + ".bin"]) == 3188
    files["README_RU.txt"] = NOTICE_STABLE
    files["original_BUILD_INFO.json"] = (FIRMWARE / "BUILD_INFO.json").read_bytes()
    return package_zip(
        out, "Lazarus-SoftW-RS232-v1.1.0-STABLE.zip", files,
        dict(product="Lazarus SoftW RS232", version="1.1.0",
             status="stable-tested-single-link", mcu="GD32F103C8T6",
             hxtal_hz=16000000, host_baud=38400, rs232_baud=38400,
             format="8N1", binary_base="0x08000000",
             real_hardware_testing="2026-09-30: one ADL-200A exchange",
             note="Original v1.1.0 firmware bytes unchanged",
             source="https://github.com/granyov/gd32-rs232-bridge")
    )


def build_release(out, builddir):
    stem = "lazarus-softw-rs232-hse16000000-38400-38400"
    files = {
        "firmware/" + stem + suffix: (builddir / (stem + suffix)).read_bytes()
        for suffix in (".bin", ".hex")
    }
    assert b"Lazarus SoftW RS232 1.2.0" in files["firmware/" + stem + ".bin"]
    if len(files["firmware/" + stem + ".bin"]) >= 62 * 1024:
        raise RuntimeError("Binary may overlap reserved Flash config pages")
    files["README_RU.txt"] = NOTICE_RELEASE
    files["CONFIGURATION.md"] = (ROOT / "docs/CONFIGURATION.md").read_bytes()
    files["BOARD_AND_FLASHING.md"] = (ROOT / "docs/BOARD_AND_FLASHING.md").read_bytes()
    return package_zip(
        out, "Lazarus-SoftW-RS232-v1.2.0-WORKING.zip", files,
        dict(product="Lazarus SoftW RS232", version="1.2.0",
             status="software-tested-not-hardware-tested", mcu="GD32F103C8T6",
             hxtal_hz=16000000, host_baud_default=38400,
             rs232_baud_default=38400, format_default="8N1",
             binary_base="0x08000000", config_slots=["0x0800F800", "0x0800FC00"],
             source_commit=git_commit(),
             source_branch="main",
             warning="NOT tested on LAZARUS UVON physical boards")
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=ROOT / "dist")
    p.add_argument("--build", type=Path, default=DEFAULT_BUILD)
    args = p.parse_args()
    for pkg in (build_stable(args.output), build_release(args.output, args.build)):
        print(f"OK {pkg.name} ({pkg.stat().st_size} bytes; SHA256 {sha256(pkg.read_bytes())})")


if __name__ == "__main__":
    main()
