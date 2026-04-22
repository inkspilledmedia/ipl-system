# IPL Match Template Generator

Deterministic pipeline that fills your HEAD TO HEAD template with real match
data, team colors, and top-performer predictions — without altering the
original design.

## Quick start

```bash
# 1. Drop real PNGs into the three asset folders (see below)
# 2. Run:
python main.py RCB CSK
# -> output/RCBvsCSK.png
```

## What you need to supply

The system ships WITHOUT sample assets. You need to add three kinds of PNG
files before it can produce a complete render. All filenames are
**case-insensitive lowercase, no spaces, no dots, no dashes, no apostrophes**.

### 1. Team logos → `assets/logos/`

One PNG per team, named by the team code. These drive **both** the logo
pasted into the stat band circles AND the automatic background recoloring
(the system extracts each logo's dominant color and tints the template halves
to match).

```
assets/logos/rcb.png
assets/logos/csk.png
assets/logos/mi.png
assets/logos/rr.png
assets/logos/kkr.png
assets/logos/lsg.png
assets/logos/gt.png
assets/logos/dc.png
assets/logos/pbks.png
assets/logos/srh.png
```

Ideally transparent-background PNGs, 300×300 or larger. The team's brand
color should dominate the logo pixels — this is usually automatic for real
IPL logos.

### 2. Captain photos → `assets/captains/`

One head-and-shoulders cutout per team, transparent background. Replaces the
grey silhouettes behind "HEAD TO HEAD".

```
assets/captains/rcb.png   # Faf du Plessis (or whoever captains RCB)
assets/captains/csk.png   # Ruturaj Gaikwad
...
```

Aim for roughly 400×500 with the head near the top. The renderer fits each
image to 160×300 (left) / 170×300 (right) with aspect preserved.

### 3. Player photos → `assets/players/`

One cutout per player, filename = lowercase-no-spaces of the player's name.

```
assets/players/viratkohli.png
assets/players/msdhoni.png
assets/players/matheeshapathirana.png
assets/players/bhuvneshwarkumar.png
```

The renderer fits each to ~152×160 inside the card rectangles.

**Missing files are handled gracefully** — the pipeline prints a `[warn]`
and continues, leaving that slot empty. This means you can start with just a
few players and add more over time.

## How predictions work

See `engine/predictor.py`. Five factors, each min-max normalized 0–100:

| Factor           | Weight | Bats source          | Bowls source         |
| ---------------- | ------ | -------------------- | -------------------- |
| Skill            | 0.35   | `avg` + `strike_rate`| `wickets` + `1/economy` |
| Recent form      | 0.25   | `recent_form`        | `recent_form`        |
| H2H vs opponent  | 0.25   | `vs_opponent_avg`    | `vs_opponent_avg`    |
| Venue / home     | 0.15   | `home_boost`         | `home_boost`         |

Hard filters run **before** scoring:

- `active == 1` — retired players excluded (Jofra Archer, DK, etc.)
- `current_team == requested_team` — handles transfers automatically

To update predictions, edit `data/players.csv`. To mark a player retired,
set `active = 0`. To move a player to a new team, change `current_team`.

## How background recoloring works

See `engine/colorizer.py`. On each render:

1. Extract the dominant non-neutral color from each team's logo PNG
   (histogram bucketing + mean inside the top bucket — ignores
   white/black/grey pixels).
2. Recolor the left half with team A's hue, the right half with team B's.
   **Only** pixels whose hue matches the source pink/red are shifted —
   everything else (silhouettes, text, gradients, stadium floor) is
   untouched. Each pixel's saturation and brightness are preserved, so
   shadows and highlights survive intact.

This means the template's design (diagonals, card shapes, rounding, stat
band layout) stays pixel-identical to the original; only the hue of the
colored elements changes.

## Project layout

```
ipl_system/
├── main.py                    pipeline entry point
├── templates/
│   └── base_template.png      the HEAD TO HEAD template (your artwork)
├── engine/
│   ├── data_fetcher.py        H2H stats + venue lookup + live-fetch stub
│   ├── predictor.py           5-factor scoring with active/team filters
│   ├── colorizer.py           dominant color extraction + HSV recolor
│   └── renderer.py            PIL overlay, all coordinates measured
├── data/
│   ├── matches.csv            IPL head-to-head with venues
│   ├── players.csv            squads with active + current_team flags
│   └── teams.csv              team → home venue mapping
├── assets/
│   ├── logos/                 YOU supply these
│   ├── captains/              YOU supply these
│   └── players/               YOU supply these
└── output/                    generated renders land here
```

## Determinism

Same input always produces byte-identical output (verified via MD5). No
randomization anywhere — ties in player scores are broken alphabetically.
