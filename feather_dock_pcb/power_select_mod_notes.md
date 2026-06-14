# Feather Dock — power architecture notes

Status: **decided and implemented in the schematic** (see "Current architecture" below).
This file keeps the *history* of how the dock powers a Feather, because there is no
perfect solution — each option trades a different thing away, and a future revision may
want to revisit. The chosen design is recorded first; rejected alternatives follow with
enough detail to re-evaluate them.

Goal: power a standard Adafruit Feather *or* a Circuit Dojo nRF9151 Feather (Nordic
nPM1300 PMIC) from one dock unit, ideally with no per-install configuration to set wrong.

---

## Decision: inject 5 V via VBUS (single universal mode)

The dock buck is set to **5 V** and drives the Feather **VBUS** pin. Every Feather accepts
5 V on VBUS and makes its own 3.3 V (or 2.8 V) from it, so this needs **no selector switch**
and works with *any* Feather board — the single power architecture we wanted.

The cost — accepted deliberately — is two things the earlier designs bought:

1. **No centralized stiff 3.3 V.** The dock's display, GPIO expander, QWIIC and pull-ups
   are now fed *back* from the Feather's own 3V3 pin — i.e. each board's onboard regulator,
   which is current-limited and is **2.8 V on the nRF9151** (BUCK1). QWIIC and the dock
   peripherals run at whatever the installed Feather regulates, and only when a Feather is
   installed and powered.
2. **"USB always safe to plug in" becomes conditional.** The dock now *sources* VBUS, which
   is the same net as the Feather's USB-connector VBUS (no diode inside the Feather to hide
   behind). Plugging USB into a docked board while the dock is also powered backfeeds the
   host. This is bounded and mild (see "Backfeed severity"), and the operating rule is
   **"supply VDC *or* plug in USB, not both."** The hardware makes the USB-only case clean
   on its own (see "Why USB-only is still safe").

We judged the universal-any-Feather, no-switch win worth those costs for prod-otyping.

### Current architecture (as built in `feather_dock_pcb.kicad_sch`)

Verified from the exported netlist:

- `U4` LMR38020 buck, `VIN` = **VDC** (screw J8, 4.2–60 V), `EN` tied to `VIN` → **buck runs
  iff VDC is present.** Input snubber R1 (2 Ω) + C12 (4.7 µF) on VDC.
- Buck output net is **VBUS**: L1 (15 µH) → VBUS, with C14 (47 µF) output cap and the FB
  divider sensing there. **R11 = 40.2 k / R12 = 10 k → 1.0 V × (1+40.2/10) = 5.02 V.**
- **VBUS** = buck output + Feather VBUS pin (J9.3). Nothing else.
- **`+3.3V`** (display FPC1, GPIO expander U2, QWIIC J10/J13, I²C pull-ups R3/R4, screw J1)
  is now sourced **from the Feather 3V3 pin** (J4.2). No buck connection — it is downstream
  of the Feather's regulator.
- Feather **EN** pin (J9.2) left **no-connect** (the Feather's internal pull-up enables its
  own regulator — do **not** ground it).
- **D1 and D2 removed entirely** (they belonged to the old input-only VBUS scheme; see
  "Why D1 had to go"). Only D18 (power-on indicator LED) remains.

### Why D1 had to go (the one non-obvious gotcha)

In the previous design D1 was anode=VBUS, cathode=VDC, making VBUS an *input* that fed VIN.
Once the buck *sources* VBUS, leaving D1 in place would have:

1. **Backfed the buck's own input** — 5 V out → VBUS → D1 → ~4.7 V onto VIN (an ugly
   undefined loop when VDC is absent), and
2. **Destroyed the USB-safe property** — USB-only (VDC absent): USB 5 V → D1 → VIN → `EN`=VIN
   turns the buck *on* → buck drives VBUS → the dock starts sourcing VBUS off USB power,
   dragging the dock's whole load (and inrush) through the host port.

So D1 was deleted. This is the single change that makes the architecture behave.

### Why USB-only is still safe (the arbitration you get for free)

You can't detect "USB present" from the dock — the contention happens on the VBUS pin,
internal to the Feather, where no dock-side series element can be inserted. But you *can*
gate on **VDC**, and the buck already does (`EN` = VIN). So the hardware enforces:

> **dock drives VBUS ⇔ VDC is present.**

- **VDC absent, USB present:** buck unpowered and off (high-Z). USB cleanly owns VBUS; dock
  peripherals run off the Feather regulator. Fully safe — this is the normal reflash/debug
  case.
- **VDC present, USB present:** the only unprotected case. Two stiff ~5 V sources on VBUS.
  Because the LMR38020 (non-F) runs auto/PFM with **diode emulation**, when USB holds VBUS
  at/above the buck's setpoint the buck simply stops switching and does **not** sink reverse
  current — it idles rather than fighting. Contention is mild and current-limited.

⚠️ **Do not substitute the LMR38020*F* (forced-PWM) variant** — it reverse-conducts and would
turn the both-present case into the buck actively pulling current back through the USB port.

### Backfeed severity (if the "don't do both" rule is broken)

At a regulated, current-limited (~2 A) 5.0 V, sourcing into a host port is rude but rarely
damaging:
- **USB-C/PD** ports are designed to tolerate VBUS being sourced (DRP/hub behavior) — robust.
- **Legacy USB-A**: host VBUS usually sits behind a load switch. Host on → both ~5 V, trivial
  current. Host off → dock 5 V can leak through the switch body diode into the host's 5 V
  rail (phantom-powering part of it, or confusing a PD controller). Rarely damaging.
- The dangerous cases (over-voltage on VBUS, or unlimited current) do **not** apply here.

Bottom line: out of USB spec, electrically rude, occasional weird enumeration/sleep
behavior, very seldom destructive at 5 V.

### Open / optional decisions

- **VBUS transient protection (decided).** The old D2 (5.6 V zener) went away with the
  input-only scheme; VBUS is now a USB-facing node, so a fresh unidirectional TVS is placed
  as **D1**, cathode→VBUS, anode→GND. Part: **SMF6.0A, LCSC C19077499** (Hongjiacheng,
  SOD-123FL): 6 V standoff (off below USB's 5.25 V max), 7.37 V breakdown, 10.3 V clamp @
  19.4 A, 200 W, IEC 61000-4-2. The 10.3 V clamp is only reached at full surge current —
  the 47 µF VBUS bulk + the Feather's input caps dominate the response for realistic
  ESD/hot-plug edges, so downstream never sees it. Chosen over the SMBJ6.0A (C19077560, SMB
  package, 600 W / 58 A): same knees, just more surge headroom for line-surge classes this
  short USB/Feather node won't see — overkill. Footprint `Diode_SMD:D_SOD-123F`. *(Note: the
  refdes D1 is reused from the deleted OR-ing diode; it is now the TVS, an entirely different
  part.)*
- **Setpoint: keep 5.02 V (decided).** Earlier idea was to trim *down* (~4.9 V) so USB
  "wins" the both-present case and the dock cleanly idles. Rejected: USB VBUS isn't a precise
  5.0 V either (spec 4.75–5.25 V, sags under load), so a 4.9 V dock still ends up *higher*
  than a drooping USB port and sources into it anyway — you'd have to drop below the USB
  minimum (~4.4–4.75 V) to robustly lose, which wastes margin for a case you avoid by
  procedure regardless. So pick the setpoint for the case that matters — **dock-only, where
  you want a clean ~5 V rail.** 4.9 V *would* be perfectly in spec and harmless downstream
  (every VBUS→3.3 V regulator has margin to spare; almost nothing on a Feather uses VBUS
  directly), it just doesn't buy reliable arbitration. Bonus: 5.02 V reads as "5.0" on a
  meter — no "oh right, 4.9 is nominal here" mental footnote during bring-up.
- **ERC PWR_FLAGs (done).** `+3.3V` is now driven by a passive connector pin (J4.2) and
  `VBUS` by a passive inductor pin, which would otherwise trip "input power pin not driven."
  `PWR_FLAG`s are placed on GND (#FLG01), VDC (#FLG02), VBUS (#FLG03) and +3.3V (#FLG05), and
  **ERC passes.** Note: these flags are virtual and do **not** appear in a `kicad-cli` netlist
  export — check the `.kicad_sch` (or run ERC) to verify them, not the netlist. Re-run ERC via
  the KiBot fab flow before ordering anyway — it's the only automated check this board has.

### Firmware / per-board notes

- **nRF9151:** its 3V3 pin is BUCK1 (default 2.8 V). The dock's `+3.3V` rail (display, QWIIC)
  therefore runs at 2.8 V unless BUCK1 is raised in software. With VBUS = 5 V there's plenty
  of headroom to set BUCK1 to 3.3 V if desired.
- Any board: the dock display/buttons/QWIIC have **no power without an installed, powered
  Feather**, and J1's "3.3 V" screw terminal inherits the same dependency and voltage.

---

## Alternative A (rejected): DPDT `3V3 / VBAT` injection selector

The prior plan: keep the dock buck at **3.3 V** and push it *into* the Feather, with a DPDT
switch choosing **where**. Rejected in favor of the universal 5 V plan because it reintroduces
a per-install setting and only supports two known board families — but it preserved the stiff
centralized 3.3 V, so keep it documented.

The mod was framed as one decision — **where the dock pushes 3.3 V into the Feather** — with
the enable (EN) handling as a *consequence*, not a separate setting:

| Inject point | Onboard regulator | EN must be |
| --- | --- | --- |
| **3V3 pin** (drive post-regulator rail) | bypassed | **GND** (disable it) |
| **VBAT pin** (drive pre-regulator input) | left running | **released / high** |

Because both poles follow from one switch position, no illegal combination is reachable.

**Board-family asymmetry (the reason it's not truly universal):**
- **Adafruit Feather** → **3V3-inject.** Dock 3.3 V drives the 3V3 pin; grounding EN disables
  the onboard LDO so there's no contention. Clean, stiff 3.3 V. (VBAT-inject also works but
  gives ~3.0–3.1 V via LDO dropout and risks charger backfeed — avoid.)
- **nRF9151 Feather** → **must use VBAT-inject.** Its 3V3 pin is a buck output (BUCK1), so
  injecting there back-drives the buck; and its EN ties to the nPM1300 **SHPHLD**, so
  grounding EN puts the whole PMIC in ship/hibernate. 3V3-inject is simply unavailable.

Silkscreen would read **`3V3 / VBAT`** (the physical action), not "Adafruit / nRF9151".

**The mod: one DPDT selector (+ one cap).** Position **3V3** = original behavior; **VBAT** =
nRF9151.

| Pole | Common | Position **3V3** | Position **VBAT** |
| --- | --- | --- | --- |
| 1 — power route | `+3.3V` | → Feather **3V3 pin** | → Feather **VBAT pin** |
| 2 — enable | Feather **EN** | → **GND** | → `+3.3V` *(or NC)* |

Net changes vs. the original input-only board: cut the hard `+3.3V`→3V3-pin link and route
it through Pole 1; cut the hard EN→GND link and route EN through Pole 2; add a
`+3.3V`→VBAT-pin path; **add a few hundred µF of bulk at the VBAT pin** (no battery to
reservoir the nRF9151 modem's ~1 A TX bursts — the cap supplies the burst so the switch
contact carries only average current); leave VBUS / D1 / D2 / J1 unchanged.

Selection details: drive Pole-2 "VBAT" throw to `+3.3V` (holds SHPHLD high on the rail its
internal pull-up uses → PMIC guaranteed on). Spec the power pole **≥ 1 A** continuous; the
~300 mA pedal-style DPDT slides are underrated. Solder-jumper equivalent rejected — the
requirement was *swap per install* and discrete jumpers reintroduce the "set it wrong" risk.

**Firmware coupling (a downside):** nothing on the dock can stop the nPM1300 from trying to
charge "the battery" (= our 3.3 V rail) if Zephyr enables charging — that pushes CC/CV
current onto our rail. **Charging must be disabled** in devicetree/runtime for VBAT-inject.
Optionally raise BUCK1 to 3.3 V (feed 3.3 V, not 2.8 V, to keep LDO headroom).

---

## Alternative B (superseded): input-only VBUS, fixed 3.3 V

The original board before either mod: buck makes **3.3 V** and drives the 3V3 pin directly;
VBUS is **input-only** via D1 (anode=VBUS, cathode=VDC) with D2 (5.6 V zener) clamping
VBUS→GND. USB 5 V flowed *into* the dock to power the buck, and high-voltage VDC could never
reach the Feather VBUS pin. This gave the safest USB story ("always safe to plug in") and a
stiff centralized 3.3 V, but only ever powered the 3V3 pin of an Adafruit-style Feather — no
nRF9151 support, which is what kicked off this whole exploration. Superseded by the 5 V plan;
its D1/D2 are the components now removed.
