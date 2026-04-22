"""Template renderer — overlays text, player photos, and team logos onto the
base HEAD TO HEAD template (1080x1350).

All coordinates measured directly from template pixels via color scanning.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from engine.colorizer import extract_dominant_color, recolor_region
from engine.team_colors import get_team_colors


# Source colors sampled from the template — used as "from" hues when
# recoloring the halves. These are the pink/red pixels in the original
# template that should be replaced with each team's brand color.
SRC_LEFT_PINK  = (180, 40, 100)   # RR pink / maroon family
SRC_RIGHT_RED  = (160,  5,   5)   # RCB red family

# Recolor regions — one rectangle per half, carefully excluding the center
# stat band and the bottom stadium texture. The hue/saturation filter inside
# recolor_region() protects text, silhouettes, shadows, and neutral pixels.
RECOLOR_REGIONS = {
    "left": [
        (0, 0, 540, 1350),
    ],
    "right": [
        (540, 0, 1080, 1350),
    ],
    # Center strip split at x=540 so left team recolors left half of strip
    # and right team recolors right half. Preserves 50-50 color divide.
    "center_above_left":  [(509, 0, 540, 185)],
    "center_above_right": [(540, 0, 565, 185)],
    "center_below_left":  [(509, 275, 540, 1350)],
    "center_below_right": [(540, 275, 565, 1350)],
}


TEMPLATE_SIZE = (1080, 1350)

POSITIONS = {
    # --- stat digits: wipe the original "00", redraw at center ---
    "teamA_wins":    {"center": (363, 565), "wipe": (310, 522, 420, 605)},
    "total_matches": {"center": (539, 530), "wipe": (478, 487, 600, 578)},
    "teamB_wins":    {"center": (713, 565), "wipe": (660, 522, 770, 605)},

    # --- team logo circles flanking the stat band ---
    # Original RR pink circle is at x=0-160 y=460-610, RCB white circle at
    # x=910-1066 y=460-610. We pad by 5px so the new logo fully covers the
    # original circle (no ghost RR/RCB outline poking out).
    "logoA": (-5,  455, 175, 165),
    "logoB": (905, 455, 175, 165),

    # --- captain silhouettes behind the title ---
    # Captain photo should DOMINATE the upper-half (matches reference renders).
    # Box is sized so the photo extends from near top to past the stat band,
    # fully covering the grey silhouette. Width ~320 fills nearly half the
    # image. Photo's head sits where the silhouette head was (y ~120-280)
    # and body extends down to ~560.
    "captainA": (10,  100, 360, 480),
    "captainB": (710, 100, 360, 480),

    # --- player photo cards ---
    "teamA_bat1":  (92,  808, 151, 154),
    "teamA_bat2":  (274, 808, 151, 154),
    "teamA_bowl1": (119, 1028, 152, 163),
    "teamA_bowl2": (301, 1028, 152, 163),
    "teamB_bat1":  (652, 810, 152, 159),
    "teamB_bat2":  (834, 810, 152, 159),
    "teamB_bowl1": (622, 1028, 173, 151),
    "teamB_bowl2": (807, 1028, 152, 151),

    # --- yellow name strips directly under each card ---
    "teamA_bat1_name":  {"center": (167, 977),  "wipe": (90,  963, 245, 1000)},
    "teamA_bat2_name":  {"center": (349, 977),  "wipe": (272, 963, 427, 1000)},
    "teamA_bowl1_name": {"center": (195, 1203), "wipe": (119, 1192, 275, 1225)},
    "teamA_bowl2_name": {"center": (377, 1203), "wipe": (301, 1192, 457, 1225)},
    "teamB_bat1_name":  {"center": (728, 984),  "wipe": (650, 968, 808, 1005)},
    "teamB_bat2_name":  {"center": (910, 984),  "wipe": (833, 968, 990, 1005)},
    "teamB_bowl1_name": {"center": (703, 1203), "wipe": (627, 1185, 779, 1218)},
    "teamB_bowl2_name": {"center": (886, 1203), "wipe": (805, 1185, 963, 1218)},
}

COLOR_WIN_GOLD_A = (246, 196,  40)   # team A win digits (was pink in template, now gold to match refs)
COLOR_TOTAL_GOLD = (246, 196,  40)
COLOR_WIN_GOLD_B = (246, 196,  40)
COLOR_NAME       = ( 20,  20,  20)
COLOR_NAME_STRIP = (242, 200,  10)


_FONT_CACHE: dict[tuple, ImageFont.FreeTypeFont] = {}
FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"


def _load_named_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a specific named font: 'anton' (Impact substitute, for HEAD and
    numbers), 'montserrat' (for player names), 'humane' (Bebas Neue, for TO)."""
    key = (name, size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    paths = {
        "anton": FONTS_DIR / "Anton-Regular.ttf",
        "montserrat": FONTS_DIR / "Montserrat-Bold.ttf",
        "humane": FONTS_DIR / "Humane-Regular.ttf",
    }
    p = paths.get(name)
    if p and p.exists():
        f = ImageFont.truetype(str(p), size)
        _FONT_CACHE[key] = f
        return f
    # fallback
    return _load_font(size)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Legacy Oswald loader kept for backwards compatibility."""
    key = ("oswald", size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    oswald = FONTS_DIR / "Oswald-Variable.ttf"
    if oswald.exists():
        f = ImageFont.truetype(str(oswald), size)
        try:
            f.set_variation_by_name("Bold")
        except Exception:
            pass
        _FONT_CACHE[key] = f
        return f
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        if Path(p).exists():
            f = ImageFont.truetype(p, size)
            _FONT_CACHE[key] = f
            return f
    return ImageFont.load_default()


def _player_filename(name: str) -> str:
    s = name.lower()
    for ch in [" ", ".", "-", "'"]:
        s = s.replace(ch, "")
    return s + ".png"


def _load_image_safe(path: Path, size: tuple) -> Image.Image | None:
    if not path.exists():
        print(f"  [warn] missing image: {path.name}")
        return None
    img = Image.open(path).convert("RGBA")
    img.thumbnail(size, Image.LANCZOS)
    return img


def _load_image_fill_width(path: Path, target_w: int, max_h: int) -> Image.Image | None:
    """Load an image and scale it so its WIDTH matches target_w. Aspect ratio
    preserved, height becomes whatever it needs to be (capped at max_h).
    Used for captains so they actually fill the silhouette width instead of
    being thumbnailed to a small centered square."""
    if not path.exists():
        print(f"  [warn] missing image: {path.name}")
        return None
    img = Image.open(path).convert("RGBA")
    iw, ih = img.size
    new_w = target_w
    new_h = int(ih * (target_w / iw))
    if new_h > max_h:
        new_h = max_h
        new_w = int(iw * (max_h / ih))
    return img.resize((new_w, new_h), Image.LANCZOS)


def _cover_fit(img: Image.Image, target_size: tuple[int, int],
               anchor: str = "center") -> Image.Image:
    """Resize image to FILL target_size while preserving aspect ratio.
    Crops the excess based on anchor:
      'center' — crop equally from both sides (default)
      'top'    — keep the top of the image, crop from bottom
    """
    tw, th = target_size
    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    new_w = int(iw * scale)
    new_h = int(ih * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - tw) // 2
    if anchor == "top":
        top = 0
    else:
        top = (new_h - th) // 2
    return img.crop((left, top, left + tw, top + th))


def blend_captain(base_image: Image.Image,
                  captain_path: Path,
                  center_position: tuple[int, int],
                  size: tuple[int, int] = (380, 420),
                  circle_center: tuple[int, int] = (80, 530),
                  circle_radius: int = 95) -> None:
    """Paste captain photo with shoulder blending BEHIND the logo circle.

    Uses cover-fit to preserve the captain's natural proportions (no
    horizontal squish). The portion that overlaps the logo circle is
    masked out with a soft fade so the logo can be drawn on top cleanly.
    """
    if not captain_path.exists():
        print(f"  [warn] missing captain: {captain_path.name}")
        return

    cap = Image.open(captain_path).convert("RGBA")
    # Top-anchored cover-fit: preserves head, crops excess from bottom
    cap = _cover_fit(cap, size, anchor="top")

    cap_arr = np.array(cap)
    alpha = cap_arr[:, :, 3].copy().astype(np.float32)

    cx, cy = center_position
    px = cx - size[0] // 2
    py = cy - size[1] // 2

    lcx = circle_center[0] - px
    lcy = circle_center[1] - py
    ys, xs = np.mgrid[0:size[1], 0:size[0]]
    dist = np.sqrt((xs - lcx) ** 2 + (ys - lcy) ** 2)

    # Soft fade right at the circle edge
    fade_width = 12
    inner = circle_radius
    mask_factor = np.clip((dist - inner + fade_width) / fade_width, 0, 1)
    mask_factor = np.where(dist < (inner - fade_width), 0, mask_factor)
    alpha = alpha * mask_factor

    cap_arr[:, :, 3] = alpha.astype(np.uint8)
    cap = Image.fromarray(cap_arr, "RGBA")
    base_image.paste(cap, (px, py), cap)


def paste_logo(base_image: Image.Image,
               logo_path: Path,
               center_position: tuple[int, int],
               diameter: int = 155) -> None:
    """Paste a logo fully visible inside a circular slot.

    The logo is scaled to fit a slightly smaller area (90% of diameter)
    then placed on a diameter-sized canvas so there's padding around it.
    This ensures edge text like "ROYAL CHALLENGERS BANGALORE" isn't
    clipped by the circular mask.
    """
    if not logo_path.exists():
        print(f"  [warn] missing logo: {logo_path.name}")
        return

    logo = Image.open(logo_path).convert("RGBA")
    # Scale to fit inside 90% of the diameter (leaves 5% padding on each side)
    inner = int(diameter * 0.88)
    logo.thumbnail((inner, inner), Image.LANCZOS)
    # Center on a diameter x diameter canvas
    centered = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    ox = (diameter - logo.width) // 2
    oy = (diameter - logo.height) // 2
    centered.paste(logo, (ox, oy), logo)

    cx, cy = center_position
    px = cx - diameter // 2
    py = cy - diameter // 2
    base_image.paste(centered, (px, py), centered)


def paste_player(base_image: Image.Image,
                 player_name: str,
                 position: tuple[int, int],
                 assets_dir: Path,
                 size: tuple[int, int] = (150, 150)) -> None:
    """Paste a player photo filling the ENTIRE card box, all 4 corners.

    Reference measurements: player face fills the full 151x154 card box
    edge-to-edge. The photo is resized to exactly match `size` — no
    cropping, no padding, just a direct resize that stretches to fill.
    The user's source photos are already face/upper-body shots.
    """
    fname = player_name.lower()
    for ch in [" ", ".", "-", "'"]:
        fname = fname.replace(ch, "")
    fname += ".png"
    path = assets_dir / "players" / fname
    print(f"  player: {path}")

    if not path.exists():
        print(f"  [warn] missing player image: {fname}")
        return

    img = Image.open(path).convert("RGBA")
    # Resize to FILL the card box exactly — all 4 corners
    img = img.resize(size, Image.LANCZOS)
    base_image.paste(img, position, img)


def _paste_centered(canvas: Image.Image, img: Image.Image, box: tuple) -> None:
    x, y, w, h = box
    iw, ih = img.size
    canvas.paste(img, (x + (w - iw) // 2, y + (h - ih) // 2), img)


def _draw_text_centered(draw, text, center, font, color):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    cx, cy = center
    draw.text((cx - tw // 2 - bbox[0], cy - th // 2 - bbox[1]),
              text, font=font, fill=color)


def _blur_wipe(canvas: Image.Image, box: tuple, radius: int = 10) -> None:
    """Blur a region so the existing text dissolves into the local background.
    New text drawn on top fully hides the blur."""
    x1, y1, x2, y2 = box
    region = canvas.crop((x1, y1, x2, y2))
    blurred = region.filter(ImageFilter.GaussianBlur(radius=radius))
    blurred = blurred.filter(ImageFilter.GaussianBlur(radius=radius))
    canvas.paste(blurred, (x1, y1))


def _sample_wipe(canvas: Image.Image, box: tuple, sample_offset: int = 8) -> None:
    """Wipe a digit slot by sampling a pixel just OUTSIDE the wipe box (above
    it, where the background is clean) and flood-filling the box with that
    color. Cleaner than blurring when the region is a flat color band."""
    x1, y1, x2, y2 = box
    # sample pixel just above the wipe box, at horizontal center
    sx = (x1 + x2) // 2
    sy = max(0, y1 - sample_offset)
    sample = canvas.getpixel((sx, sy))
    if len(sample) == 4:
        sample = sample[:3] + (255,)
    ImageDraw.Draw(canvas).rectangle(box, fill=sample)


def _name_strip_wipe(canvas: Image.Image, box: tuple) -> None:
    ImageDraw.Draw(canvas).rectangle(box, fill=COLOR_NAME_STRIP)


def _fit_font(text, max_w, start_size, loader):
    size = start_size
    while size >= 11:
        f = loader(size)
        b = f.getbbox(text)
        if (b[2] - b[0]) <= max_w:
            return f
        size -= 1
    return loader(8)


def render_template(
    template_path: str,
    output_path: str,
    team_a: str,
    team_b: str,
    stats: dict,
    team_a_players: dict,
    team_b_players: dict,
    assets_dir: str,
    font_overrides: dict = None,
) -> str:
    assets = Path(assets_dir)
    canvas = Image.open(template_path).convert("RGBA")
    fo = font_overrides or {}

    # ---- resolve team color profiles ----
    # Priority: hardcoded TEAM_COLORS dict (single source of truth, includes
    # win-digit color) -> logo dominant color extraction -> skip recolor.
    profile_a = get_team_colors(team_a)
    profile_b = get_team_colors(team_b)

    color_a = profile_a["background"] if profile_a else None
    color_b = profile_b["background"] if profile_b else None

    if color_a is None:
        logo_a_path = assets / "logos" / f"{team_a.lower()}.png"
        if logo_a_path.exists():
            color_a = extract_dominant_color(str(logo_a_path))
            print(f"  {team_a} color (from logo): {color_a}")
        else:
            print(f"  [warn] no profile or logo for {team_a}, skipping recolor")
    else:
        print(f"  {team_a} color (from dict): {color_a}")

    if color_b is None:
        logo_b_path = assets / "logos" / f"{team_b.lower()}.png"
        if logo_b_path.exists():
            color_b = extract_dominant_color(str(logo_b_path))
            print(f"  {team_b} color (from logo): {color_b}")
        else:
            print(f"  [warn] no profile or logo for {team_b}, skipping recolor")
    else:
        print(f"  {team_b} color (from dict): {color_b}")

    # ---- recolor template halves ----
    # Two passes per side: first the background diagonals (source = pink/red),
    # then the player cards (source = bright pink/red card fills). Tolerance
    # is kept tight (0.10) so gold elements like the "TO" letters in HEAD TO
    # HEAD (hue ~0.14) survive untouched — gold is far enough from red/pink
    # in hue space that a 0.10 tolerance won't catch it.
    if color_a is not None:
        for region in RECOLOR_REGIONS["left"]:
            recolor_region(canvas, region, SRC_LEFT_PINK, color_a,
                           hue_tolerance=0.15)
            recolor_region(canvas, region, (255, 70, 145), color_a,
                           hue_tolerance=0.15)
            # Third pass: catch any remaining reddish/purple pixels
            recolor_region(canvas, region, (160, 30, 90), color_a,
                           hue_tolerance=0.15)
            # Fourth pass: dark purple pixels leaking into left zone
            recolor_region(canvas, region, (35, 13, 49), color_a,
                           hue_tolerance=0.15)
    if color_b is not None:
        for region in RECOLOR_REGIONS["right"]:
            recolor_region(canvas, region, SRC_RIGHT_RED, color_b,
                           hue_tolerance=0.15)
            recolor_region(canvas, region, (174, 0, 1), color_b,
                           hue_tolerance=0.15)
            recolor_region(canvas, region, (100, 0, 50), color_b,
                           hue_tolerance=0.15)
            # Fourth pass: dark red-purple at bottom
            recolor_region(canvas, region, (60, 5, 0), color_b,
                           hue_tolerance=0.15)

    # Recolor the center strip (x=509-564) above and below the "TO" letters.
    # Left half of strip (x=509-540) uses LEFT team color only.
    # Right half of strip (x=540-565) uses RIGHT team color only.
    # This preserves the 50-50 color divide at x=540.
    if color_a is not None:
        for region_key in ["center_above_left", "center_below_left"]:
            for region in RECOLOR_REGIONS[region_key]:
                recolor_region(canvas, region, SRC_LEFT_PINK, color_a,
                               hue_tolerance=0.15)
                recolor_region(canvas, region, (255, 70, 145), color_a,
                               hue_tolerance=0.15)
                recolor_region(canvas, region, (160, 30, 90), color_a,
                               hue_tolerance=0.15)
                recolor_region(canvas, region, (35, 13, 49), color_a,
                               hue_tolerance=0.15)
    if color_b is not None:
        for region_key in ["center_above_right", "center_below_right"]:
            for region in RECOLOR_REGIONS[region_key]:
                recolor_region(canvas, region, SRC_RIGHT_RED, color_b,
                               hue_tolerance=0.15)
                recolor_region(canvas, region, (174, 0, 1), color_b,
                               hue_tolerance=0.15)
                recolor_region(canvas, region, (100, 0, 50), color_b,
                               hue_tolerance=0.15)
                recolor_region(canvas, region, (60, 5, 0), color_b,
                               hue_tolerance=0.15)

    # ============================================================
    # RENDER PIPELINE
    # ============================================================

    # ---- ERASE baked-in HEAD TO HEAD title BEFORE captain paste ----
    # Baked title spans y=166-279. We sample row y=158 (just above title)
    # and copy it down across the title area to remove it cleanly.
    canvas_arr = np.array(canvas)
    sample_row = canvas_arr[158:159, :, :].copy()
    for y in range(160, 285):
        canvas_arr[y, :, :] = sample_row[0, :, :]
    canvas = Image.fromarray(canvas_arr, "RGBA")

    # ---- captain photos (shoulder blends behind circle) ----
    # Center at y=320 (was 310). Top edge = 320-210 = 110. This gives 10px
    # more room at the top so tall heads (like Pant's) don't get clipped.
    blend_captain(canvas, assets / "captains" / f"{team_a.lower()}.png",
                  center_position=(200, 320),
                  circle_center=(75, 535), circle_radius=95)
    blend_captain(canvas, assets / "captains" / f"{team_b.lower()}.png",
                  center_position=(880, 320),
                  circle_center=(1000, 535), circle_radius=95)

    # ---- team logos ON TOP of captain shoulders ----
    # CSK logo: shifted slightly down-left per user request
    # KKR logo: shifted slightly down-right per user request
    paste_logo(canvas, assets / "logos" / f"{team_a.lower()}.png",
               center_position=(75, 535), diameter=155)
    paste_logo(canvas, assets / "logos" / f"{team_b.lower()}.png",
               center_position=(1000, 535), diameter=155)

    # ---- player photos (no text yet, that comes after) ----
    def place_players(tp, prefix):
        slots = [
            (f"{prefix}_bat1",  tp["batsmen"][0] if len(tp["batsmen"])  > 0 else None),
            (f"{prefix}_bat2",  tp["batsmen"][1] if len(tp["batsmen"])  > 1 else None),
            (f"{prefix}_bowl1", tp["bowlers"][0] if len(tp["bowlers"]) > 0 else None),
            (f"{prefix}_bowl2", tp["bowlers"][1] if len(tp["bowlers"]) > 1 else None),
        ]
        for slot_key, name in slots:
            if name is None:
                continue
            box = POSITIONS[slot_key]
            paste_player(canvas, name, (box[0], box[1]), assets,
                         size=(box[2], box[3]))

    place_players(team_a_players, "teamA")
    place_players(team_b_players, "teamB")

    # ============================================================
    # ALL TEXT DRAWING (LAST — sits on top of everything)
    # ============================================================

    # ---- stat digits (Anton font, Impact substitute) ----
    digit_a = profile_a["win_digit"] if profile_a else COLOR_TOTAL_GOLD
    digit_b = profile_b["win_digit"] if profile_b else COLOR_TOTAL_GOLD
    stat_font = _load_named_font('anton', fo.get('stat_digits') or 72)
    for key, color in [
        ("teamA_wins",    digit_a),
        ("total_matches", COLOR_TOTAL_GOLD),
        ("teamB_wins",    digit_b),
    ]:
        slot = POSITIONS[key]
        _sample_wipe(canvas, slot["wipe"], sample_offset=8)
        text = str(stats[key]).zfill(2)
        _draw_text_centered(ImageDraw.Draw(canvas), text,
                            slot["center"], stat_font, color)

    # ---- player names on yellow strips (Montserrat) ----
    montserrat_loader = lambda s: _load_named_font('montserrat', s)
    name_max = fo.get('player_name_max') or 22
    name_two_max = fo.get('player_name_two_line_max') or 20
    def draw_player_names(tp, prefix):
        slots = [
            (f"{prefix}_bat1",  tp["batsmen"][0] if len(tp["batsmen"])  > 0 else None),
            (f"{prefix}_bat2",  tp["batsmen"][1] if len(tp["batsmen"])  > 1 else None),
            (f"{prefix}_bowl1", tp["bowlers"][0] if len(tp["bowlers"]) > 0 else None),
            (f"{prefix}_bowl2", tp["bowlers"][1] if len(tp["bowlers"]) > 1 else None),
        ]
        for slot_key, name in slots:
            if name is None:
                continue
            name_slot = POSITIONS[f"{slot_key}_name"]
            _name_strip_wipe(canvas, name_slot["wipe"])
            strip_w = name_slot["wipe"][2] - name_slot["wipe"][0] - 6
            draw = ImageDraw.Draw(canvas)
            parts = name.upper().split()
            if len(parts) >= 2:
                display = parts[0][0] + ". " + " ".join(parts[1:])
            else:
                display = name.upper()
            f = _fit_font(display, strip_w, name_max, montserrat_loader)
            _draw_text_centered(draw, display, name_slot["center"],
                                f, COLOR_NAME)

    draw_player_names(team_a_players, "teamA")
    draw_player_names(team_b_players, "teamB")

    # ---- NEW TITLE: HEAD (Anton) + TO (Humane WHITE) + HEAD (Anton) ----
    # Drawn LAST so it sits on top of everything (captains, logos, etc.)
    # Smaller size than the original baked-in title so captain heads don't
    # hide behind it. White "TO" instead of gold.
    draw = ImageDraw.Draw(canvas)
    head_font = _load_named_font('anton', fo.get('title_head') or 95)
    to_font = _load_named_font('humane', fo.get('title_to') or 110)

    # Measure text widths
    head_text = "HEAD"
    head_bbox = draw.textbbox((0, 0), head_text, font=head_font)
    head_w = head_bbox[2] - head_bbox[0]
    head_h = head_bbox[3] - head_bbox[1]

    to_text = "TO"
    to_bbox = draw.textbbox((0, 0), to_text, font=to_font)
    to_w = to_bbox[2] - to_bbox[0]
    to_h = to_bbox[3] - to_bbox[1]

    # Layout: HEAD ... TO ... HEAD, centered horizontally at y=200 (above captains)
    gap = 18
    total_w = head_w + gap + to_w + gap + head_w
    title_y = 175
    start_x = (1080 - total_w) // 2

    # Draw left "HEAD" in white
    draw.text((start_x - head_bbox[0], title_y - head_bbox[1]),
              head_text, font=head_font, fill=(255, 255, 255))

    # Draw right "HEAD" in white
    right_head_x = start_x + head_w + gap + to_w + gap
    draw.text((right_head_x - head_bbox[0], title_y - head_bbox[1]),
              head_text, font=head_font, fill=(255, 255, 255))

    # Draw "TO" in WHITE Humane, centered between the two HEADs
    to_x = start_x + head_w + gap
    # Vertically center TO with HEAD (TO is taller, shift down to align baselines)
    to_y = title_y + (head_h - to_h) // 2
    draw.text((to_x - to_bbox[0], to_y - to_bbox[1]),
              to_text, font=to_font, fill=(255, 255, 255))

    final = Image.new("RGB", canvas.size, (0, 0, 0))
    final.paste(canvas, mask=canvas.split()[3])
    final.save(output_path, "PNG")
    return output_path
