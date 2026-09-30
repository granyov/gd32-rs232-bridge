# Third-party components

The project's MIT license does not replace the licenses of third-party components.

- `Drivers/CMSIS/`: Arm CMSIS and GigaDevice device headers/system startup files; copyright and redistribution terms are retained in each file.
- `Drivers/GD32F10x_standard_peripheral/`: GigaDevice standard peripheral library; copyright and redistribution terms are retained in each file.
- `Drivers/LICENSE-GigaDevice`: upstream repository license, SLA-GD0001-version1.1.
- `Core/Startup/startup_gd32f103c8.s`: GCC startup implementation with vector order derived from GigaDevice's `startup_gd32f10x_md.s`; upstream notice/license retained in this file and the original vendor startup distributed in `Drivers/CMSIS/GD/GD32F10x/Source/ARM/`.

Upstream: https://github.com/GigaDevice-GD32-MCU/GD32F10x_Firmware_Library

Commit: `23a80f96368336b4d47014da33cd9b7ba550165e`.

Changes to the vendor system-clock source are recorded in `SDK_CHANGES.patch`. Other vendor files are included without modification.

The original HDLC application, supplied hardware schematic PDF and original firmware ZIP are not part of this repository.
