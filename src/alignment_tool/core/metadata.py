"""Best-effort pixel-size (um/pixel) metadata reading.

Per spec S5.2: metadata is an optional pre-fill only, never a dependency. Every
function here returns None on anything unexpected (missing tag, unknown format,
unparseable XML) rather than raising -- absence of metadata is a normal, fully
supported outcome, not an error condition.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

_UNIT_TO_MICROMETRES = {
    "um": 1.0,
    "µm": 1.0,  # µm
    "micron": 1.0,
    "microns": 1.0,
    "nm": 1e-3,
    "mm": 1e3,
    "cm": 1e4,
    "m": 1e6,
}


def _convert_to_um(value: float, unit: str | None) -> float:
    if not unit:
        return value
    factor = _UNIT_TO_MICROMETRES.get(unit.strip().lower())
    return value * factor if factor is not None else value


def _pixels_element(ome_xml: str) -> ET.Element | None:
    try:
        root = ET.fromstring(ome_xml)
    except ET.ParseError:
        return None
    for elem in root.iter():
        if elem.tag.rsplit("}", 1)[-1] == "Pixels":
            return elem
    return None


def read_pixel_size_um(path: Path) -> float | None:
    """Read an isotropic pixel size (um/pixel) from OME-XML TIFF metadata, if any.

    Only TIFF/OME-TIFF realistically carries this; any other format (JPEG, PNG, ...)
    returns None immediately, matching spec S5.2's "JPEG has physically lost it."
    """
    path = Path(path)
    if path.suffix.lower() not in {".tif", ".tiff"}:
        return None

    try:
        import tifffile
    except ImportError:
        return None

    try:
        with tifffile.TiffFile(str(path)) as tif:
            ome_xml = tif.ome_metadata
    except Exception:
        return None

    if not ome_xml:
        return None

    pixels = _pixels_element(ome_xml)
    if pixels is None:
        return None

    size_x = pixels.get("PhysicalSizeX")
    if size_x is None:
        return None

    try:
        value = float(size_x)
    except ValueError:
        return None

    unit = pixels.get("PhysicalSizeXUnit")
    return _convert_to_um(value, unit)


def compute_prefill_scale(flat_um_per_px: float | None, ihc_um_per_px: float | None) -> float | None:
    """Shared batch scale pre-fill, only when BOTH sides have metadata (spec S5.2).

    scale maps flat-image pixel distances to IHC-image pixel distances:
    ihc_px = flat_px * scale, and physical size must match: flat_px * flat_umpp
    == ihc_px * ihc_umpp, so scale = flat_umpp / ihc_umpp.
    """
    if flat_um_per_px is None or ihc_um_per_px is None:
        return None
    if ihc_um_per_px == 0:
        return None
    return flat_um_per_px / ihc_um_per_px
