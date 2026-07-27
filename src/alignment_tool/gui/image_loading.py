"""Load a flat/IHC image as a numpy array (re-exported from core.image_io --
see there) and render it to a QPixmap under a display-only min/max contrast
remap (spec S8.2). The remap only ever affects what's rendered on screen --
the source file and the in-memory array it was read from are never modified
or written back.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtGui import QImage, QPixmap

from alignment_tool.core.image_io import load_image_array

__all__ = ["load_image_array", "array_to_qpixmap"]


def array_to_qpixmap(arr: np.ndarray, display_min: float | None, display_max: float | None) -> QPixmap:
    lo = display_min if display_min is not None else float(arr.min())
    hi = display_max if display_max is not None else float(arr.max())
    if hi <= lo:
        hi = lo + 1.0
    scaled = np.clip((arr - lo) / (hi - lo), 0.0, 1.0) * 255.0
    img8 = np.ascontiguousarray(scaled.astype(np.uint8))
    height, width = img8.shape
    qimage = QImage(img8.data, width, height, width, QImage.Format.Format_Grayscale8)
    return QPixmap.fromImage(qimage.copy())  # .copy() so the pixmap owns its own buffer
