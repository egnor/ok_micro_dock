# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

OK Micro Dock is a mixed hardware + firmware repository for "dock" baseboards that carry standard-format microcontroller boards (primarily [Adafruit Feather](https://www.adafruit.com/category/943)). A dock adds a wide-input switching power supply, screw terminals, QWIIC/Stemma QT connectors, a tiny OLED display, and buttons. The repo holds the KiCad PCB designs *and* an Arduino driver library for the display/button interface. Intended for "prod-otyping" (escape rooms, immersive installations): robust wiring, observability, quick part swaps.

## Layout

- `src/` — Arduino driver library (`ok_micro_dock.h` / `.cpp`). Exposed as a library via `library.properties`.
- `feather_dock_pcb/`, `usb_serial_pcb/`, `xbee_dock_pcb/` — three independent KiCad 7+ projects, each a self-contained board design. (`xbee_dock_pcb` was historically named `station_pcb`; its backups/fab files still use that name.)

This repo depends on **sibling** checkouts under `../` (not submodules):
- `../ok_pcb_parts` — shared KiCad symbol/footprint library (`OK` lib) and the shared KiBot fab config. Every board's `fp-lib-table`, `sym-lib-table`, and `make_fab.kibot.yaml` reference it by relative path, so it must be checked out next to this repo.
- `../ok_arduino_little_layout` (`OK Little Layout`), `../ok_arduino_logging` (`OK Logging`), plus `U8g2` — Arduino library deps declared in `library.properties`.

## Firmware architecture

The driver is a thin I2C abstraction over the dock's onboard peripherals (see `src/ok_micro_dock.cpp`):
- `ok_dock_init_feather_v8()` brings up, on the shared I2C bus, a PI4IOE5V6408 GPIO expander (I2C `0x43`) for the three buttons and an SSD1306-compatible 64x32 OLED (I2C `0x3C`).
- Display output goes through `ok_dock_layout` (an `OkLittleLayout` from the sibling library) wrapping a U8g2 device. On init failure it stays a `DummyLayout` (no-op) so callers never hit a null pointer.
- `ok_dock_button(int which)` reads buttons 0–2 from the GPIO expander (active-low).
- The `_feather_v8` / version suffixes are meaningful: hardware revisions change which chips are populated, so init code is version-specific. Match firmware init to the board revision.

## Git LFS

`.kicad_pcb`, `.kicad_sch`, `.zip`, and media files are stored in **Git LFS** (see `.gitattributes`). After cloning, run `git lfs install --local && git lfs pull` (mise runs this automatically as a `postinstall` hook). When editing or diffing PCB/schematic files, expect LFS pointers rather than text in a fresh checkout.

## Common commands

Tooling is managed by [mise](https://mise.jdx.dev) (`mise.toml`). Run `mise install` to set up; its postinstall hook initializes LFS.

Generate JLCPCB fab outputs (Gerbers, drill, BOM, CPL) for a board — run from inside that board's directory:
```
cd feather_dock_pcb && kibot -c make_fab.kibot.yaml
```
Each `make_fab.kibot.yaml` imports `../../ok_pcb_parts/kibot_jlcpcb.yaml`, which runs ERC + DRC preflight and writes outputs to that board's `fab/` directory (gitignored). The Arduino library has no separate build step — it is consumed by an Arduino sketch that depends on it.

**Python 3.14 (Ubuntu 26.04 "Resolute" and later):** the apt-packaged KiBot 1.9.0 (and its bundled `mcpyrate` 3.6.0) crash at import time under Python 3.14, which removed the deprecated `ast.Num`/`ast.Str` classes and `ast.Constant.s`/`.n` shims they still use (`AttributeError: 'Constant' object has no attribute 's'` / `module 'ast' has no attribute 'Num'`). This is a distro transition gap, unrelated to KiCAD 10 or any board file. Until a 3.14-compatible KiBot ships, run fab through the bundled wrapper, which patches those names back in (no system files touched):
```
cd feather_dock_pcb && python3 ../tools/kibot314.py -c make_fab.kibot.yaml
```
On a Python that still has these names (≤ 3.13), the wrapper's shims are no-ops, so it's safe to use everywhere. For fully reproducible/CI fab runs, the `inti-cmnb` Docker images (e.g. `kicad10_auto`) pin a matched KiCAD+Python+KiBot set and sidestep the host Python entirely — heavier, but worth it if you want guaranteed-reproducible outputs.

## Conventions

- There is no test suite; correctness is verified via KiCad ERC/DRC (run during the KiBot fab step) and on real hardware.
- `fab/`, `*-backups/`, `.history/`, and `*.kicad_prl` are gitignored — don't commit generated or local-state files.
