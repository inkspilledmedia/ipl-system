"""Team-color extraction and template recoloring.

Responsibilities:
1. Extract a team's dominant color from its logo PNG (ignores white/black/
   transparent pixels so we get the *brand* color, not the background).
2. Recolor the template's left/right background halves to the team colors.
3. Recolor the pink player cards (team A) and red player cards (team B) to
   the new team colors while preserving the card shapes pixel-for-pixel.

All recoloring is HSV hue-shift + saturation/value preservation — this means
shadows, highlights, and gradients in the original template are kept intact;
only the base hue changes. That way the design aesthetic (diagonals, depth,
card rounding) stays identical to the source template.
"""
from pathlib import Path
from PIL import Image
import numpy as np
from collections import Counter


# -- color buckets we treat as "not a brand color" when extracting from a logo
def _is_neutral(r: int, g: int, b: int) -> bool:
    if max(r, g, b) < 40:           # near-black
        return True
    if min(r, g, b) > 220:          # near-white
        return True
    if abs(r - g) < 12 and abs(g - b) < 12 and abs(r - b) < 12:  # grey
        return True
    return False


def extract_dominant_color(logo_path: str) -> tuple[int, int, int]:
    """
    Return the dominant *brand* color of a logo (RGB tuple).
    Strategy: histogram-bucket the non-transparent, non-neutral pixels at
    coarse granularity (32-level buckets), pick the most common bucket, then
    average the pixels inside that bucket for a clean RGB value.
    """
    img = Image.open(logo_path).convert("RGBA")
    arr = np.array(img)
    h, w, _ = arr.shape

    # Keep only visible (alpha > 128), non-neutral pixels
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    visible = a > 128
    pixels = arr[visible][:, :3]  # Nx3

    if len(pixels) == 0:
        return (128, 128, 128)

    # Drop neutrals
    mask = np.array([not _is_neutral(int(p[0]), int(p[1]), int(p[2]))
                     for p in pixels])
    brand = pixels[mask]
    if len(brand) == 0:
        brand = pixels  # all neutral — fall back

    # Bucket into 32-level histogram and find the mode
    buckets = (brand // 32) * 32
    keys = [tuple(row) for row in buckets]
    mode_bucket, _ = Counter(keys).most_common(1)[0]

    # Average the pixels inside that bucket for a precise brand color
    in_bucket = np.all(buckets == np.array(mode_bucket), axis=1)
    mean = brand[in_bucket].mean(axis=0)
    return (int(mean[0]), int(mean[1]), int(mean[2]))


# ---------------------------------------------------------------------------
# HSV-preserving recolor: replace the hue of every pixel in a region with the
# target hue, but keep each pixel's original saturation & value. This means
# highlights, shadows, and gradients survive unchanged; only the hue flips.
# ---------------------------------------------------------------------------
def _rgb_to_hsv_np(rgb: np.ndarray) -> np.ndarray:
    """Vectorized RGB->HSV. rgb shape (..., 3), values 0-255. Returns same
    shape with H in [0,1], S in [0,1], V in [0,1]."""
    r = rgb[..., 0] / 255.0
    g = rgb[..., 1] / 255.0
    b = rgb[..., 2] / 255.0
    mx = np.max(rgb, axis=-1) / 255.0
    mn = np.min(rgb, axis=-1) / 255.0
    v = mx
    s = np.where(mx > 0, (mx - mn) / np.where(mx > 0, mx, 1), 0)
    diff = mx - mn
    h = np.zeros_like(mx)
    # Avoid divide-by-zero
    safe = diff > 1e-6
    rc = np.where(safe & (mx == r), (g - b) / np.where(safe, diff, 1), 0)
    gc = np.where(safe & (mx == g), 2.0 + (b - r) / np.where(safe, diff, 1), 0)
    bc = np.where(safe & (mx == b), 4.0 + (r - g) / np.where(safe, diff, 1), 0)
    h = (rc + gc + bc) / 6.0
    h = np.where(h < 0, h + 1, h)
    return np.stack([h, s, v], axis=-1)


def _hsv_to_rgb_np(hsv: np.ndarray) -> np.ndarray:
    h = hsv[..., 0]
    s = hsv[..., 1]
    v = hsv[..., 2]
    i = np.floor(h * 6).astype(int)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    i = i % 6
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    rgb = np.stack([r, g, b], axis=-1) * 255
    return rgb.clip(0, 255).astype(np.uint8)


def _hue_of(rgb: tuple[int, int, int]) -> float:
    arr = np.array([[list(rgb)]], dtype=np.uint8)
    return float(_rgb_to_hsv_np(arr)[0, 0, 0])


def recolor_region(
    canvas: Image.Image,
    region: tuple[int, int, int, int],       # (x1, y1, x2, y2)
    source_hue_rgb: tuple[int, int, int],    # the template's original color in this region
    target_rgb: tuple[int, int, int],        # target team color
    hue_tolerance: float = 0.08,             # how tight to match the source hue
) -> None:
    """
    Recolor pixels in `region` that match the `source_hue_rgb` hue. Pixels
    whose hue is far from the source (e.g. white text, dark shadows on a
    different-hued element) are left alone. The new color preserves each
    pixel's original saturation/value so gradients stay intact.
    """
    x1, y1, x2, y2 = region
    crop = canvas.crop((x1, y1, x2, y2)).convert("RGBA")
    arr = np.array(crop)
    rgb = arr[..., :3].astype(np.uint8)
    alpha = arr[..., 3]

    src_h = _hue_of(source_hue_rgb)
    tgt_h = _hue_of(target_rgb)

    hsv = _rgb_to_hsv_np(rgb)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    # Hue distance on the circular space (0..1, wraps)
    dh = np.abs(h - src_h)
    dh = np.minimum(dh, 1 - dh)

    # Only recolor pixels that are (a) close to the source hue and
    # (b) actually saturated (skip near-greys and whites to preserve text)
    match = (dh < hue_tolerance) & (s > 0.15) & (v > 0.08)

    new_hsv = hsv.copy()
    new_hsv[..., 0] = np.where(match, tgt_h, h)
    new_rgb = _hsv_to_rgb_np(new_hsv)

    out = np.dstack([new_rgb, alpha])
    canvas.paste(Image.fromarray(out, "RGBA"), (x1, y1))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(extract_dominant_color(sys.argv[1]))
