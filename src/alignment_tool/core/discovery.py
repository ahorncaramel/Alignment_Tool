"""Recording discovery and the spec-S4.4 pre-flight report.

Recording identity comes from the folder structure only (spec S4.1) -- no
external lookup. Every recording found under an experiment folder is reported
in exactly one of four states; none is ever silently dropped (spec S4.4).
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from alignment_tool.core.session import PreflightEntry, RecordingState

_REC_FOLDER_RE = re.compile(r"^Rec_(\d+)_(\d+)_(\d+)$")

STATUS_PRESENT = "present"
STATUS_MISSING = "missing"
STATUS_SUSPECTED_MISSPELLING = "suspected_misspelling"
STATUS_UNREADABLE = "unreadable"

_FUZZY_CUTOFF = 0.6  # difflib similarity ratio; tuned loose since "did you mean" is a
# suggestion the user confirms/rejects, not an automatic decision.


@dataclass
class DiscoveredRecording:
    full_id: str
    short_number: int
    folder: Path
    status: str
    flat_image_path: Path | None = None
    suggested_filename: str | None = None


def _expected_stem(full_id: str) -> str:
    return f"Flatrec_{full_id}"


def read_image_dimensions(path: Path) -> tuple[int, int] | None:
    """(width, height) in pixels, or None if the image can't be opened."""
    try:
        with Image.open(path) as im:
            return im.size
    except Exception:
        pass
    if path.suffix.lower() in {".tif", ".tiff"}:
        try:
            import tifffile

            with tifffile.TiffFile(str(path)) as tif:
                page = tif.pages[0]
                return (page.imagewidth, page.imagelength)
        except Exception:
            return None
    return None


def can_read_image(path: Path) -> bool:
    """Best-effort "is this actually openable" check, distinguishing S4.4's
    'present but unreadable' from 'present & readable'.
    """
    try:
        with Image.open(path) as im:
            im.load()
        return True
    except Exception:
        pass
    if path.suffix.lower() in {".tif", ".tiff"}:
        try:
            import tifffile

            tifffile.TiffFile(str(path)).asarray()
            return True
        except Exception:
            return False
    return False


def find_experiments(processing_root: Path) -> list[tuple[str, Path]]:
    """Return (experiment_id, experiment_folder) for every Ex_* folder found
    directly under an OP_* folder beneath processing_root (spec S4.1), sorted
    by name. Naming is matched by prefix only ("OP_", "Ex_"), not a strict
    numbering pattern, since the exact op/exp numbering scheme may vary.
    """
    results = []
    root = Path(processing_root)
    if not root.is_dir():
        return results
    for op_folder in sorted(root.iterdir()):
        if not op_folder.is_dir() or not op_folder.name.startswith("OP_"):
            continue
        for ex_folder in sorted(op_folder.iterdir()):
            if ex_folder.is_dir() and ex_folder.name.startswith("Ex_"):
                results.append((ex_folder.name, ex_folder))
    return results


def find_recording_folders(experiment_folder: Path) -> list[tuple[str, int, Path]]:
    """Return (full_id, short_number, folder) for every Rec_* subfolder,
    sorted by recording number.
    """
    results = []
    for entry in Path(experiment_folder).iterdir():
        if not entry.is_dir():
            continue
        match = _REC_FOLDER_RE.match(entry.name)
        if match:
            results.append((entry.name, int(match.group(3)), entry))
    results.sort(key=lambda item: item[1])
    return results


def scan_experiment(experiment_folder: Path) -> list[DiscoveredRecording]:
    """Scan one Ex_* folder and classify every recording's flat image per S4.4."""
    discovered: list[DiscoveredRecording] = []

    for full_id, short_number, folder in find_recording_folders(experiment_folder):
        expected_stem = _expected_stem(full_id)
        files_in_folder = [f for f in folder.iterdir() if f.is_file()]

        exact_matches = [f for f in files_in_folder if f.stem.lower() == expected_stem.lower()]

        if exact_matches:
            flat_path = sorted(exact_matches)[0]
            if can_read_image(flat_path):
                status = STATUS_PRESENT
            else:
                status = STATUS_UNREADABLE
            discovered.append(
                DiscoveredRecording(
                    full_id=full_id,
                    short_number=short_number,
                    folder=folder,
                    status=status,
                    flat_image_path=flat_path,
                )
            )
            continue

        candidate_stems = [f.stem.lower() for f in files_in_folder]
        close = difflib.get_close_matches(expected_stem.lower(), candidate_stems, n=1, cutoff=_FUZZY_CUTOFF)
        if close:
            suggested = next(f.name for f in files_in_folder if f.stem.lower() == close[0])
            discovered.append(
                DiscoveredRecording(
                    full_id=full_id,
                    short_number=short_number,
                    folder=folder,
                    status=STATUS_SUSPECTED_MISSPELLING,
                    suggested_filename=suggested,
                )
            )
        else:
            discovered.append(
                DiscoveredRecording(
                    full_id=full_id,
                    short_number=short_number,
                    folder=folder,
                    status=STATUS_MISSING,
                )
            )

    return discovered


def to_preflight_entries(discovered: list[DiscoveredRecording]) -> list[PreflightEntry]:
    return [
        PreflightEntry(
            full_id=d.full_id,
            status=d.status,
            matched_filename=d.flat_image_path.name if d.flat_image_path else None,
            suggested_filename=d.suggested_filename,
        )
        for d in discovered
    ]


def build_initial_recordings(discovered: list[DiscoveredRecording]) -> list[RecordingState]:
    """One RecordingState per discovered recording, present or not (spec S4.4:
    nothing is silently dropped). `placement` is left None -- the GUI assigns an
    initial position once it lays the recording out for the user to pick up.
    Recordings without a readable flat image simply have no width/height/placement
    until (if ever) that's fixed and the experiment is rescanned.
    """
    recordings = []
    for d in discovered:
        width = height = None
        if d.status == STATUS_PRESENT and d.flat_image_path is not None:
            dims = read_image_dimensions(d.flat_image_path)
            if dims is not None:
                width, height = dims
        recordings.append(
            RecordingState(
                full_id=d.full_id,
                short_number=d.short_number,
                flat_image_path=str(d.flat_image_path) if d.flat_image_path else None,
                width_px=width,
                height_px=height,
            )
        )
    return recordings
