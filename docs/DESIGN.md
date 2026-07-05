# Splitrail — "MEET SHEET" design system

Instrument-panel / timing-system aesthetic: a sprint timing gate crossed with a
mountaineering altimeter. The three effort modes are three genuinely different
instruments, because that's the physiological truth of the training.

## Effort modes

| Mode | Meaning | Color | Instrument | Geometry |
|---|---|---|---|---|
| `explosive` | sprint / anaerobic power (neural work) | Gate Red | **GATE** | typographic — hero digits + beam delta, no chart |
| `aerobic` | sustained endurance (engine work) | Steel | **STRIP** | horizontal — continuous strip-chart trace |
| `loaded` | ruck/hike under load (structural work) | Scree | **ALTI** | vertical — relief column vs. goal line |

Design test: delete the labels — you should still tell the instruments apart by
shape alone. If a change makes them look like "three cards with different accent
colors", revert it.

## Tokens

### Color (the only six colors in the app)

| Token | Hex | Role |
|---|---|---|
| Chalk | `#EFEAE0` | Background — warm paper, meet timing sheet / topo map |
| Ink | `#16181D` | Text, frames, baseline rules |
| Graphite | `#565A63` | Secondary text, axis labels |
| Gate Red | `#C33B2A` | Explosive mode; also alerts and PB marks |
| Steel | `#2F5D7C` | Aerobic mode traces |
| Scree | `#6B6349` | Loaded mode relief |

Derived (not new tokens): `Hairline` = Ink @ 22% alpha; `ChalkShade` `#E5DFD2`
for inset areas.

### Type

| Role | Face | Rule |
|---|---|---|
| Display | **Anton** | Exactly once per screen — the hero readout. Never labels. |
| Body | **IBM Plex Sans** | Prose, notes. |
| Data | **IBM Plex Mono** | Every number in the app. Labels: caps + 1–2sp letterspacing ("engraved"). |

Fonts are bundled in `android/app/src/main/res/font/` (OFL, converted from
Fontsource woff2 releases).

### Layout rules

- No cards, no shadows, no rounded containers. Sections separated by 1dp
  hairline rules like a printed timing sheet.
- 20dp horizontal margins; instruments own their internal grids.
- Light "meet sheet" theme only for now; a future inverted "night ops" variant
  swaps Chalk↔Ink for alpine starts.

## Signature element: THE RAIL

Week-long timing tape at the top of the Dashboard. One horizontal baseline =
time axis. Sprint sessions are red gate ticks cutting the rail (best split
printed above), aerobic sessions are steel bands along the rail (length ∝
duration), loaded sessions are olive relief rising off the rail (height ∝ vert
gain). Month view = the tape zoomed out; weekly reports embed a rail thumbnail;
the launcher icon is its 3-glyph distillation (tick / band / peak).

## Self-critique log (kept honest)

- Rejected: dark mode + neon defaults, rounded stat cards, radial rings,
  "mode triangle" radar chart (generic AI-chart thinking).
- Dropped a 6th "signal amber" token — alerts reuse Gate Red.
- Watch: Braun/Teenage-Engineering pastiche. No skeuomorphs, no fake hardware;
  the aesthetic must come from timing-sheet conventions (hairlines, engraved
  caps, tabular digits).
- Watch: Anton overuse → Nike-ad territory. One hero number per screen, ever.
