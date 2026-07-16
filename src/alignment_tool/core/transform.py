"""Pure similarity-transform math: window (flat-image) frame <-> IHC image frame.

No GUI imports here (spec S12) - this module must be usable and testable standalone.

Coordinate/convention contract (must match the CSV export in export.py exactly):
  - IHC frame: origin at the IHC image's top-left corner, +x right, +y down (pixels).
  - Window-local frame: origin at the flat image's top-left corner, +x right, +y down,
    same units as the flat image's own pixels (before scale is applied).
  - x, y (on SimilarityPlacement) are the *window centre*'s position in the IHC frame.
  - theta_deg is degrees, positive = counter-clockwise as a person looks at the screen
    (i.e. visually CCW under the y-down convention above -- NOT the textbook CCW matrix,
    which would look clockwise on screen once y is flipped). See _rotate() below.
  - scale is unitless and shared across the whole batch: ihc_length = window_length * scale.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SimilarityPlacement:
    """Per-recording placement. Scale is intentionally NOT a field here (spec S5.1):
    it is a single value shared by the whole session, supplied separately to every
    function below, so it is structurally impossible for two placements to disagree.
    """

    theta_deg: float
    x: float
    y: float


def _rotate(dx: float, dy: float, theta_deg: float) -> tuple[float, float]:
    """Rotate (dx, dy) by theta_deg, positive = visually counter-clockwise on screen
    under a y-down axis convention. See module docstring for why this is the mirror
    of the textbook CCW rotation matrix.
    """
    theta = math.radians(theta_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    return (
        dx * cos_t + dy * sin_t,
        -dx * sin_t + dy * cos_t,
    )


def _rotate_inverse(dx: float, dy: float, theta_deg: float) -> tuple[float, float]:
    return _rotate(dx, dy, -theta_deg)


def window_to_ihc(
    local_point: tuple[float, float],
    window_size: tuple[float, float],
    scale: float,
    placement: SimilarityPlacement,
) -> tuple[float, float]:
    """Map a point in window-local pixel coordinates to the IHC frame.

    local_point: (x, y) in the flat image's own pixel coordinates (top-left origin).
    window_size: (width, height) of the flat image in pixels, used to find its centre.
    """
    width, height = window_size
    dx = local_point[0] - width / 2.0
    dy = local_point[1] - height / 2.0
    dx, dy = dx * scale, dy * scale
    rdx, rdy = _rotate(dx, dy, placement.theta_deg)
    return (placement.x + rdx, placement.y + rdy)


def ihc_to_window(
    ihc_point: tuple[float, float],
    window_size: tuple[float, float],
    scale: float,
    placement: SimilarityPlacement,
) -> tuple[float, float]:
    """Inverse of window_to_ihc: map an IHC-frame point back to window-local pixels."""
    width, height = window_size
    dx = ihc_point[0] - placement.x
    dy = ihc_point[1] - placement.y
    rdx, rdy = _rotate_inverse(dx, dy, placement.theta_deg)
    rdx, rdy = rdx / scale, rdy / scale
    return (rdx + width / 2.0, rdy + height / 2.0)
