"""Session state, JSON persistence, and in-memory undo/redo history.

Three distinct mechanisms per spec S10 (kept separate on purpose):
  - Autosave: `save_session_json` writes the *current* SessionState to the tool's own
    session store. Called on every edit. Never touches input files/folders.
  - Undo/redo: `SessionHistory` is purely in-memory, floored at the state passed to
    its constructor (the load-time snapshot). It never goes further back than that.
  - Save As: also uses `save_session_json`, just to a different (named/versioned)
    path chosen by the caller (see gui layer). Does not touch autosave or the undo
    floor.
"""

from __future__ import annotations

import dataclasses
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from alignment_tool.core.transform import SimilarityPlacement

# Tri-state marker vocabulary shared by both blinded-judgement fields below
# (activity_state, cyp11b2_state). "undecided" is the only valid starting
# state -- a recording must never be silently defaulted to "yes"/"no".
STATE_UNDECIDED = "undecided"
STATE_YES = "yes"
STATE_NO = "no"
MARKER_STATES = (STATE_UNDECIDED, STATE_YES, STATE_NO)


@dataclass
class PixelSize:
    """Best-effort pixel size in micrometres/pixel. value is None if no metadata
    was found -- absence is a normal, fully-supported state (spec S5.2), not an error.
    """

    value_um_per_px: float | None = None
    source: str = "none"  # "metadata" | "none"


@dataclass
class ContrastSettings:
    """Non-destructive display-only min/max range (spec S8.2). None means
    'use the image's natural full range' -- never written back to any file.
    """

    display_min: float | None = None
    display_max: float | None = None


@dataclass
class RecordingState:
    """One row of the eventual export. `placement` is None until the user has
    actually positioned this recording (e.g. it has no readable flat image yet,
    per the pre-flight report) -- that is a normal, expected state, not an error.
    `dropped` is a separate, explicit user decision to exclude an otherwise-placeable
    recording; it is independent of the pre-flight image status.

    `activity_state` and `cyp11b2_state` are two independent, separately-recorded
    yes/no/undecided judgements, each its own deliberately unbiased pass over the
    recordings (never inferred from the other, never inferred from placement):
      - `activity_state`: did this recording show calcium activity at all.
        Rendered on screen as a green/red outline around the window (see
        gui/window_item.py); undecided = no outline.
      - `cyp11b2_state`: does this window's placement sit over any
        CYP11B2-positive area on the IHC image at all (whole-window yes/no,
        no quantification -- a future version may refine this to per-quadrant).
        Deliberately given no on-screen visual treatment in v1, so judging it
        is never biased by a colour already drawn on the window; stored for
        export only.
    Both start "undecided" and must never be silently defaulted to yes/no.
    """

    full_id: str  # e.g. "Rec_006_03_01" -- retained everywhere, never dropped from the ID
    short_number: int  # e.g. 1 -- the on-screen label only (spec S7)
    flat_image_path: str | None
    width_px: int | None = None  # None until a readable flat image is known
    height_px: int | None = None
    placement: SimilarityPlacement | None = None
    dropped: bool = False
    # 0..9 -> 0%..90% transparency in 10-point steps (spec S8.1); 0 = fully opaque.
    transparency_step: int = 0
    contrast: ContrastSettings = field(default_factory=ContrastSettings)
    activity_state: str = STATE_UNDECIDED  # "undecided" | "yes" | "no"
    cyp11b2_state: str = STATE_UNDECIDED  # "undecided" | "yes" | "no"


@dataclass
class PreflightEntry:
    full_id: str
    status: str  # "present" | "missing" | "suspected_misspelling" | "unreadable"
    matched_filename: str | None = None
    suggested_filename: str | None = None


@dataclass
class SessionState:
    experiment_id: str  # e.g. "Ex_006_03"
    experiment_folder: str
    processing_root: str
    ihc_image_path: str | None
    ihc_transparency_step: int
    shared_scale: float
    scale_source: str  # "metadata" | "manual"
    pixel_size_flat: PixelSize
    pixel_size_ihc: PixelSize
    recordings: list[RecordingState]
    preflight_report: list[PreflightEntry]
    created_at: str
    last_modified: str
    # Session-wide gate (not per-recording): while False, placement (drag/
    # rotate/scale) is editable and activity_state/cyp11b2_state marking is
    # blinded (hidden) -- the user must make a deliberate mental commitment
    # ("I am done aligning") by locking before either judgement becomes
    # available. Toggling back and forth is expected and must never discard
    # anything already marked (see gui/main_window.py's lock toggle, which
    # only ever flips this flag). Defaults False so a freshly-created session
    # always starts in the alignment phase.
    alignment_locked: bool = False


def to_dict(session: SessionState) -> dict:
    return dataclasses.asdict(session)


def from_dict(data: dict) -> SessionState:
    recordings = [
        RecordingState(
            full_id=r["full_id"],
            short_number=r["short_number"],
            flat_image_path=r.get("flat_image_path"),
            width_px=r.get("width_px"),
            height_px=r.get("height_px"),
            placement=SimilarityPlacement(**r["placement"]) if r.get("placement") else None,
            dropped=r.get("dropped", False),
            transparency_step=r.get("transparency_step", 0),
            contrast=ContrastSettings(**r.get("contrast", {})),
            activity_state=r.get("activity_state", STATE_UNDECIDED),
            cyp11b2_state=r.get("cyp11b2_state", STATE_UNDECIDED),
        )
        for r in data["recordings"]
    ]
    preflight_report = [PreflightEntry(**p) for p in data.get("preflight_report", [])]
    return SessionState(
        experiment_id=data["experiment_id"],
        experiment_folder=data["experiment_folder"],
        processing_root=data["processing_root"],
        ihc_image_path=data.get("ihc_image_path"),
        ihc_transparency_step=data.get("ihc_transparency_step", 0),
        shared_scale=data["shared_scale"],
        scale_source=data["scale_source"],
        pixel_size_flat=PixelSize(**data["pixel_size_flat"]),
        pixel_size_ihc=PixelSize(**data["pixel_size_ihc"]),
        recordings=recordings,
        preflight_report=preflight_report,
        created_at=data["created_at"],
        last_modified=data["last_modified"],
        alignment_locked=data.get("alignment_locked", False),
    )


def save_session_json(session: SessionState, path: Path) -> None:
    """Atomic write (write to a temp file, then replace) so a crash mid-write
    can never corrupt the previous autosave.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(json.dumps(to_dict(session), indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def load_session_json(path: Path) -> SessionState:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return from_dict(data)


class SessionHistory:
    """In-memory undo/redo. Floored at the state given to __init__ (the load-point
    snapshot, per spec S10) -- that state is never itself poppable, only returned to.
    """

    def __init__(self, initial: SessionState):
        self.current = initial
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def apply(self, new_state: SessionState) -> None:
        """Record the current state as an undo point, then make new_state current.
        Call this once per discrete edit (not per intermediate drag event).
        """
        self._undo_stack.append(to_dict(self.current))
        self._redo_stack.clear()
        self.current = new_state

    def undo(self) -> SessionState:
        if not self._undo_stack:
            raise IndexError("cannot undo past load-point")
        self._redo_stack.append(to_dict(self.current))
        self.current = from_dict(self._undo_stack.pop())
        return self.current

    def redo(self) -> SessionState:
        if not self._redo_stack:
            raise IndexError("nothing to redo")
        self._undo_stack.append(to_dict(self.current))
        self.current = from_dict(self._redo_stack.pop())
        return self.current
