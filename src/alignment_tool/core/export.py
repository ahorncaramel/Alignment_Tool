"""The transform CSV and action log -- the tool's actual product (spec S11).

The CSV's comment/header block states the coordinate convention explicitly and
must stay in lockstep with transform.py's documented convention: any change to
one must be reflected in the other.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

from alignment_tool.core.session import SessionState

CONVENTION_LINES = [
    "# Coordinate convention:",
    "#   origin      = IHC image top-left corner",
    "#   +x          = right, +y = down (pixels, IHC image frame)",
    "#   x, y        = the window's CENTRE point, in the IHC image frame",
    "#   rotation    = degrees, positive = counter-clockwise as viewed on screen",
    "#   scale       = unitless; ihc_length_px = window_length_px * scale",
    "#   scale is a single value shared by every row in this file (spec S5.1)",
]

CSV_FIELDNAMES = [
    "full_id",
    "short_number",
    "status",
    "x",
    "y",
    "rotation_deg",
    "scale",
    "window_width_px",
    "window_height_px",
    "pixel_size_source",
    "ihc_image_path",
]

STATUS_PLACED = "placed"
STATUS_DROPPED = "dropped"
STATUS_NOT_PLACED = "not_placed"


def _row_status(rec, preflight_status_by_id: dict[str, str]) -> str:
    if rec.dropped:
        return STATUS_DROPPED
    if rec.placement is not None:
        return STATUS_PLACED
    preflight_status = preflight_status_by_id.get(rec.full_id)
    if preflight_status is None or preflight_status == "present":
        # image is fine but the user hasn't positioned it (yet)
        return STATUS_NOT_PLACED
    return preflight_status  # "missing" | "suspected_misspelling" | "unreadable"


def write_transform_csv(session: SessionState, out_path: Path) -> Path:
    """Write the transform table: one row per *discovered* recording (spec S4.4 --
    nothing silently dropped from the audit trail), not just the ones successfully
    placed. A recording with no placement (no readable flat image, not yet
    positioned, or explicitly dropped by the user) gets a row with its `status`
    explaining why and blank transform fields -- a missing short_number in the
    sequence is expected and unambiguous, since full_id is retained on every row.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    preflight_status_by_id = {p.full_id: p.status for p in session.preflight_report}

    buffer = io.StringIO()
    for line in CONVENTION_LINES:
        buffer.write(line + "\n")
    buffer.write(f"# scale_source: {session.scale_source}\n")
    buffer.write(
        f"# status: '{STATUS_PLACED}' rows have a real transform; all other statuses"
        " (not_placed / dropped / missing / suspected_misspelling / unreadable)"
        " leave x/y/rotation_deg/window_*_px blank\n"
    )

    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    for rec in sorted(session.recordings, key=lambda r: r.short_number):
        status = _row_status(rec, preflight_status_by_id)
        placed = status == STATUS_PLACED
        writer.writerow(
            {
                "full_id": rec.full_id,
                "short_number": rec.short_number,
                "status": status,
                "x": rec.placement.x if placed else "",
                "y": rec.placement.y if placed else "",
                "rotation_deg": rec.placement.theta_deg if placed else "",
                "scale": session.shared_scale,
                "window_width_px": rec.width_px if placed else "",
                "window_height_px": rec.height_px if placed else "",
                "pixel_size_source": session.scale_source,
                "ihc_image_path": session.ihc_image_path or "",
            }
        )

    out_path.write_text(buffer.getvalue(), encoding="utf-8", newline="")
    return out_path


@dataclass
class ActionLogEntry:
    timestamp: str
    message: str


def build_action_log(session: SessionState, export_timestamp: str) -> str:
    """Plain-text action log, paired with the CSV export (spec S11): experiment,
    IHC file used, pre-flight results, scale value/source, export time.
    """
    lines = [
        f"Experiment: {session.experiment_id}",
        f"Experiment folder: {session.experiment_folder}",
        f"IHC image used: {session.ihc_image_path}",
        f"Shared scale: {session.shared_scale} (source: {session.scale_source})",
        "",
        "Pre-flight report:",
    ]
    for entry in session.preflight_report:
        detail = ""
        if entry.matched_filename:
            detail = f" -> {entry.matched_filename}"
        elif entry.suggested_filename:
            detail = f" -> did you mean '{entry.suggested_filename}'?"
        lines.append(f"  {entry.full_id}: {entry.status}{detail}")
    lines.append("")
    lines.append(f"Export timestamp: {export_timestamp}")
    return "\n".join(lines) + "\n"


def write_action_log(session: SessionState, out_path: Path, export_timestamp: str) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_action_log(session, export_timestamp), encoding="utf-8")
    return out_path
