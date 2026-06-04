# Feather Dock — power-injection select mod (notes)

Status: **design notes only**, nothing built. Goal: let one dock unit power either a
standard Adafruit Feather *or* a Circuit Dojo nRF9151 Feather (Nordic nPM1300 PMIC),
selectable per install, without a checklist of independent jumpers you can set wrong.

## The core idea: "inject via 3V3" vs "inject via VBAT"

Think of the mod as one decision — **where the dock pushes its 3.3 V into the Feather** —
not as "Adafruit vs nRF9151". The enable (EN) handling is a *consequence* of that choice,
not a separate setting:

| Inject point | What it means | Onboard regulator | EN pin must be |
| --- | --- | --- | --- |
| **3V3 pin** | drive the *post*-regulator rail directly | bypassed (we replace it) | **GND** (disable it so it doesn't fight us) |
| **VBAT pin** | drive the *pre*-regulator input | left running | **released / high** |

Because both poles follow from one decision, a single selector cannot be set into an
illegal combination (e.g. driving the 3V3 pin while the board's regulator is still on).

### Board-family asymmetry (important)

The modes are *not* symmetric, so the practical mapping is still fixed per board:

- **Adafruit Feather** — use **3V3-inject**. Dock 3.3 V drives the 3V3 pin; grounding EN
  disables the onboard LDO so there's no contention, and the charger (if fitted) sees no
  battery on BAT. Clean, stiff 3.3 V. (VBAT-inject *also* works but gives a ~3.0–3.1 V
  rail via LDO dropout, and risks charger backfeed onto our rail when USB is plugged in —
  avoid.)
- **nRF9151 Feather** — must use **VBAT-inject**. Its 3V3 pin is a **buck output (BUCK1)**,
  so injecting there back-drives the buck; and its EN pin ties to the nPM1300 **SHPHLD**,
  so grounding EN puts the whole PMIC in ship/hibernate (everything off). So 3V3-inject is
  simply not available on this board.

Silkscreen the selector **`3V3 / VBAT`** (describes the physical action), not
"Adafruit / nRF9151".

## Verified facts this mod relies on

Dock (`feather_dock_pcb.kicad_sch`):
- `U4` LMR38020 buck makes the global `+3.3V` net (4.2–80 V in → 3.3 V).
- `+3.3V` currently drives the Feather header **3V3 pin** directly, and is already exposed
  on screw terminal **J1 ("3.3V")** and feeds display / GPIO expander / QWIIC.
- Power input is **VDC (screw term, straight to U4 VIN)** diode-OR'd with **VBUS via D1**.
  `D1` (Schottky) is **only on the VBUS leg** (anode = Feather VBUS, cathode = VIN), and
  `D2` (5.6 V zener) clamps VBUS→GND. So VBUS is an **input only** — Feather USB 5 V flows
  *into* the dock and can't flow back out, and the high-voltage VDC can never reach the
  Feather VBUS pin.
- Feather header **EN** is its own net, currently tied low.

nRF9151 Feather (`../nrf9151-feather/power.kicad_sch`):
- nPM1300 (`U2`). Header **EN → SHPHLD** (ship/enable). Header **3V3 pin = BUCK1 output**
  (default **2.8 V**, software-settable). Header **VBAT → nPM1300 VBAT** pin directly.
  Second buck → `VCC` (modem/SIM side). Both bucks run from VSYS (VBUS-or-VBAT power-path).
- NTC present (charge temp sense) — i.e. the charger *can* be enabled in firmware.

## The mod: one DPDT selector (+ one cap)

Two poles, two positions. Position **3V3** = today's behavior; position **VBAT** = nRF9151.

| Pole | Common | Position **3V3** | Position **VBAT** |
| --- | --- | --- | --- |
| 1 — power route | `+3.3V` | → Feather **3V3 pin** | → Feather **VBAT pin** |
| 2 — enable | Feather **EN** | → **GND** | → `+3.3V` *(or leave NC)* |

Net changes vs. the stock board:
1. **Cut** the hard `+3.3V` → Feather-3V3-pin connection; route it through Pole 1.
2. **Cut** the hard EN → GND connection; route EN through Pole 2.
3. **Add** a `+3.3V` → Feather-VBAT-pin path (Pole 1, VBAT throw). VBAT pin is otherwise
   unused on the dock today.
4. **Add bulk capacitance (a few hundred µF) at the Feather VBAT pin**, downstream of the
   switch. There's no battery to act as a reservoir for the nRF9151 modem's ~1 A TX
   bursts; the cap supplies the bursts so the switch contact only carries average current.
5. Leave VBUS / D1 / D2 / J1 **unchanged**.

Selection details:
- Pole-2 "VBAT" throw to `+3.3V` (not NC) holds SHPHLD high on the same rail its internal
  pull-up uses → PMIC guaranteed on, nothing floating. NC also works (ship-mode needs a
  sustained low) but driven-high is one less thing to worry about.
- **Switch rating:** spec the power pole ≥ 1 A continuous; the tiny ~300 mA pedal-style
  DPDT slides are underrated. With the bulk cap downstream, average current is modest.
- Solder-jumper equivalent is possible but rejected here: the requirement is *swap per
  install*, and discrete jumpers reintroduce the "set it wrong" risk the single switch
  removes.

## Firmware note (not a hardware item)

Nothing on the dock can stop the nPM1300 from trying to **charge "the battery" (= our
3.3 V rail)** if Circuit Dojo's Zephyr config enables charging — that would push CC/CV
current back onto our rail. **Charging must be disabled** in devicetree/runtime for the
VBAT-inject setup. Optionally raise BUCK1 from its 2.8 V default to 3.3 V in software (with
VBAT = 3.3 V there's ~0.5 V headroom, so BUCK1 regulates cleanly rather than dropping out).
**Feed 3.3 V, not 2.8 V** — a lower feed eats that headroom.

## Rejected alternative: inject 5 V via VBUS (single universal mode)

Reconfigure the dock buck to 5 V and push it into the Feather **VBUS** pin. Tempting
because every Feather accepts 5 V on VBUS, so it needs **no switch** and is in-spec for
each board's own regulator. Not chosen, because it trades away two things the current
design deliberately bought:

1. **Loses centralized 3.3 V.** The dock's stiff 3.3 V (display, GPIO expander, **QWIIC**)
   would have to come back from the Feather's 3V3 pin — i.e. each board's onboard
   regulator, which is current-limited, and on the nRF9151 is **2.8 V** (BUCK1). QWIIC at
   2.8 V and board-limited current is a downgrade. Avoiding it means adding a second
   5 V→3.3 V regulator on the dock.
2. **Loses "USB is always safe to plug in."** Today VBUS is input-only (via D1), so USB can
   be plugged into a docked board anytime for debug/reflash. 5 V-inject makes the dock
   *source* VBUS; the Feather's VBUS pin is the same net as its USB-connector VBUS (no
   diode inside the Feather to hide behind), so plugging in USB **backfeeds the host**. A
   dock-side diode can't stop it — the path is internal to the Feather. Stuffing 5 V into a
   powered-off host port ranges from harmless (port load-switch blocks it) to
   *phantom-powering* part of the host (leakage through the switch body diode / data-line
   protection into its 5 V rail), which can hold it half-on or confuse a laptop's PD
   controller. Out of USB spec for a device to source VBUS; rarely damaging at 5 V but
   electrically rude and an occasional source of weird enumeration/sleep behavior.

Keep it documented as a fallback, but the `3V3 / VBAT` selector keeps both the stiff
centralized 3.3 V and safe USB-debug.
