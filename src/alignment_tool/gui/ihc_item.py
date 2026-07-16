"""The IHC layer: bottom of the fixed z-order (spec S9), origin (0, 0) at its
top-left corner -- this item's local frame IS the IHC coordinate frame that
every window's placement (x, y) is expressed in.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QGraphicsPixmapItem

from alignment_tool.gui.image_loading import array_to_qpixmap, load_image_array


class IhcLayerItem(QGraphicsPixmapItem):
    def __init__(self, image_path: Path, parent=None):
        super().__init__(parent)
        self.image_path = Path(image_path)
        self._array = load_image_array(self.image_path)
        self.height_px, self.width_px = self._array.shape[:2]
        pixmap = array_to_qpixmap(self._array, None, None)
        self.setPixmap(pixmap)
        # Top-left origin (no offset applied): local (0, 0) IS the IHC frame origin.
        self.setZValue(0)

    def set_transparency_step(self, step: int) -> None:
        step = max(0, min(9, step))
        self.setOpacity(1.0 - step * 0.1)
