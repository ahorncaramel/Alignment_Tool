"""Rasterizes the current placement into a single flattened image in the IHC
frame: the "exported rendered overlay figure" that spec S11 explicitly
deferred ("design v1 so this could be added, but do not build it now unless
trivial") -- built now because it was directly requested and the existing
transform math makes it a small, testable addition.

Deliberately reuses transform.py's exact ihc_to_window() convention (worked
out analytically into affine coefficients below, see
test_composite.py::test_affine_coefficients_match_ihc_to_window) rather than
a rotate()-then-paste sequence from some image library, whose sign convention
would have to be independently verified. The transform math is the one thing
in this tool that already has to be right and already has tests; this module
piggybacks on that instead of re-deriving rotation direction from scratch.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from alignment_tool.core.image_io import load_image_array
from alignment_tool.core.session import SessionState

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "arialbd.ttf",
    "arial.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _normalize_to_uint8(arr: np.ndarray, display_min: float | None, display_max: float | None) -> np.ndarray:
    lo = display_min if display_min is not None else float(arr.min())
    hi = display_max if display_max is not None else float(arr.max())
    if hi <= lo:
        hi = lo + 1.0
    scaled = np.clip((arr - lo) / (hi - lo), 0.0, 1.0) * 255.0
    return scaled.astype(np.uint8)


def _affine_ihc_to_window(theta_deg: float, scale: float, px: float, py: float, win_w: int, win_h: int):
    """The 6 coefficients (a, b, c, d, e, f) such that, for any point (x, y)
    in the IHC frame, the corresponding window-local pixel is
    (a*x + b*y + c, d*x + e*y + f) -- i.e. exactly transform.ihc_to_window(),
    solved out algebraically so it can be applied to a whole image at once
    via PIL's Image.transform(..., Image.AFFINE, ...), which expects
    coefficients in this same "destination pixel -> source pixel" direction.
    """
    theta = math.radians(theta_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    a, b = cos_t / scale, -sin_t / scale
    d, e = sin_t / scale, cos_t / scale
    c = -a * px - b * py + win_w / 2.0
    f = -d * px - e * py + win_h / 2.0
    return a, b, c, d, e, f


def render_aligned_composite(session: SessionState) -> Image.Image:
    """Render IHC (base) + every placed, non-dropped recording window (on
    top, at its similarity-transform placement/contrast/opacity, labelled
    with its short number) into one RGB image, sized to the IHC image's own
    pixel extent -- the same layered composite the GUI shows (spec S9),
    flattened for use outside the tool.
    """
    if not session.ihc_image_path:
        raise ValueError("session has no IHC image to render against")

    ihc_arr = load_image_array(Path(session.ihc_image_path))
    ihc_h, ihc_w = ihc_arr.shape
    ihc_rgb = Image.fromarray(_normalize_to_uint8(ihc_arr, None, None)).convert("RGB")
    ihc_alpha = 1.0 - session.ihc_transparency_step * 0.1
    canvas = Image.blend(Image.new("RGB", (ihc_w, ihc_h), "white"), ihc_rgb, ihc_alpha)

    for rec in sorted(session.recordings, key=lambda r: r.short_number):
        if rec.dropped or rec.placement is None or not rec.flat_image_path:
            continue
        flat_path = Path(rec.flat_image_path)
        if not flat_path.exists():
            continue

        window_arr = load_image_array(flat_path)
        win_h, win_w = window_arr.shape
        gray = _normalize_to_uint8(window_arr, rec.contrast.display_min, rec.contrast.display_max)
        opacity = 1.0 - rec.transparency_step * 0.1

        a, b, c, d, e, f = _affine_ihc_to_window(
            rec.placement.theta_deg, session.shared_scale, rec.placement.x, rec.placement.y, win_w, win_h
        )

        # Bounding box of the rotated+scaled window footprint in the IHC
        # frame: any rotation of a w x h rectangle fits inside a circle of
        # radius hypot(w, h) / 2 around its centre, so this always covers the
        # true footprint (possibly with a little slack at some angles).
        half_w, half_h = (win_w * session.shared_scale) / 2.0, (win_h * session.shared_scale) / 2.0
        extent = math.hypot(half_w, half_h)
        x0 = max(0, int(math.floor(rec.placement.x - extent)))
        y0 = max(0, int(math.floor(rec.placement.y - extent)))
        x1 = min(ihc_w, int(math.ceil(rec.placement.x + extent)))
        y1 = min(ihc_h, int(math.ceil(rec.placement.y + extent)))
        if x1 <= x0 or y1 <= y0:
            continue  # placed entirely outside the IHC canvas

        # Fold the crop offset into the coefficients so they map the crop's
        # own (0, 0) instead of the full canvas's (0, 0).
        c_local, f_local = a * x0 + b * y0 + c, d * x0 + e * y0 + f
        coeffs = (a, b, c_local, d, e, f_local)
        crop_size = (x1 - x0, y1 - y0)

        src = Image.fromarray(gray, mode="L")
        patch = src.transform(crop_size, Image.AFFINE, coeffs, resample=Image.BILINEAR)

        # Same transform applied to a solid mask: opacity inside the source
        # footprint, 0 outside it -- so rotation doesn't paste square corners.
        mask_src = Image.new("L", (win_w, win_h), int(round(opacity * 255)))
        mask = mask_src.transform(crop_size, Image.AFFINE, coeffs, resample=Image.BILINEAR)

        canvas.paste(patch.convert("RGB"), (x0, y0), mask)

        font = _load_font(max(10, int(round(win_h * session.shared_scale * 0.15))))
        draw = ImageDraw.Draw(canvas)
        draw.text(
            (rec.placement.x, rec.placement.y),
            str(rec.short_number),
            fill="yellow",
            font=font,
            anchor="mm",
            stroke_width=2,
            stroke_fill="black",
        )

    return canvas


def write_aligned_composite_png(session: SessionState, out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    render_aligned_composite(session).save(out_path)
    return out_path
