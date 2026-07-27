"""Load a flat/IHC image as a numpy array. No GUI imports (spec S12) so it can
be used from both the GUI layer and core-only rendering (composite.py).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def load_image_array(path: Path) -> np.ndarray:
    path = Path(path)
    if path.suffix.lower() in {".tif", ".tiff"}:
        import tifffile

        arr = tifffile.imread(str(path))
    else:
        arr = np.array(Image.open(path).convert("L"))
    arr = np.asarray(arr)

    # OME-TIFF commonly comes back with singleton T/Z/C axes even for a plain
    # single-plane image, e.g. shape (1, 1, 1, H, W) -- drop those first.
    arr = np.squeeze(arr)

    if arr.ndim == 3 and arr.shape[-1] in (3, 4):
        arr = arr.mean(axis=-1)  # RGB/RGBA -> grayscale

    # Anything still >2D at this point isn't a single flat image (spec S4.3
    # expects the flat image to already be a pre-averaged single plane) --
    # fall back to the first plane rather than crashing on the unpack below.
    while arr.ndim > 2:
        arr = arr[0]

    return arr.astype(np.float64)
