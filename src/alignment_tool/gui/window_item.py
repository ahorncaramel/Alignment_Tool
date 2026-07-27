"""One calcium-recording flat-image window: draggable, rotatable, independently
faded, non-destructively contrast-adjusted. Position/rotation/scale here must
stay in the same convention as core/transform.py: item-local origin (0,0) is
the image CENTRE (spec: x/y refer to the window centre).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem, QGraphicsRectItem

from alignment_tool.gui.image_loading import array_to_qpixmap, load_image_array
from alignment_tool.gui.label_item import make_label

# Rotation direction note: transform.py defines positive theta_deg as visually
# counter-clockwise under a y-down axis convention. Qt's QGraphicsItem.setRotation
# is visually CLOCKWISE for positive angles in the same y-down scene coordinates,
# so every value crossing this boundary must be negated. Both directions do this
# (see .rotation_deg property and .set_placement()) -- do not "simplify" one away.


class RecordingWindowItem(QGraphicsPixmapItem):
    def __init__(
        self,
        full_id: str,
        short_number: int,
        image_path: Path,
        on_commit: Callable[["RecordingWindowItem"], None] | None = None,
        on_scale_request: Callable[[float], None] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.full_id = full_id
        self.short_number = short_number
        self.image_path = Path(image_path)
        # Fired once per discrete user action (drag release, one wheel notch), NOT
        # on every intermediate mouse-move -- otherwise a single drag would flood
        # the undo stack with one entry per pixel of motion.
        self._on_commit = on_commit
        self._on_scale_request = on_scale_request
        self._display_min: float | None = None
        self._display_max: float | None = None

        self._array = load_image_array(self.image_path)
        self.native_height_px, self.native_width_px = self._array.shape[:2]

        self._refresh_pixmap()

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.setZValue(1)

        self._label = make_label(self, str(short_number))

        # Dropped marker: a translucent red tint over the whole window, on top
        # of the image but below the number label. The window stays fully
        # visible/selectable/navigable while dropped (spec: dropped only
        # excludes it from the export, it's not deleted) -- this is purely a
        # visual "this one is excluded" cue, toggled by set_dropped().
        self._dropped = False
        self._dropped_overlay = QGraphicsRectItem(self.boundingRect(), self)
        self._dropped_overlay.setBrush(QBrush(QColor(255, 0, 0, 90)))
        self._dropped_overlay.setPen(Qt.PenStyle.NoPen)
        self._dropped_overlay.setZValue(2)
        self._dropped_overlay.setVisible(False)

    def _refresh_pixmap(self) -> None:
        pixmap = array_to_qpixmap(self._array, self._display_min, self._display_max)
        self.setPixmap(pixmap)
        # Offset the pixmap by half its size so this item's local (0, 0) -- the
        # point rotation/scale/position are defined about -- is the image centre.
        self.setOffset(-pixmap.width() / 2.0, -pixmap.height() / 2.0)

    def set_contrast(self, display_min: float | None, display_max: float | None) -> None:
        self._display_min = display_min
        self._display_max = display_max
        self._refresh_pixmap()

    def contrast(self) -> tuple[float | None, float | None]:
        return self._display_min, self._display_max

    def set_dropped(self, dropped: bool) -> None:
        self._dropped = dropped
        self._dropped_overlay.setVisible(dropped)

    def is_dropped(self) -> bool:
        return self._dropped

    def set_transparency_step(self, step: int) -> None:
        step = max(0, min(9, step))
        self.setOpacity(1.0 - step * 0.1)

    def transparency_step(self) -> int:
        return round((1.0 - self.opacity()) / 0.1)

    def set_placement(self, theta_deg: float, x: float, y: float, scale: float) -> None:
        self.set_theta_deg(theta_deg)
        self.set_scale(scale)
        self.setPos(QPointF(x, y))

    def set_scale(self, scale: float) -> None:
        """Use this instead of the inherited setScale() directly, in case
        window-scale-dependent bookkeeping is needed here later. The label is
        deliberately NOT rescaled with the window (see label_item.py) -- it
        must stay readable at any batch scale, including a small one.
        """
        self.setScale(scale)

    def set_theta_deg(self, theta_deg: float) -> None:
        self.setRotation(-theta_deg)  # see module note on rotation direction

    def centre_scene_pos(self) -> QPointF:
        return self.scenePos()

    def theta_deg(self) -> float:
        return -self.rotation()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if self._on_commit:
            self._on_commit(self)

    def wheelEvent(self, event) -> None:
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        if ctrl and self._on_scale_request:
            # Ctrl+wheel over a window == "drag-to-resize" (spec S5.3): it changes
            # the one shared batch scale, not this window alone.
            factor = 1.05 if event.delta() > 0 else 1 / 1.05
            self._on_scale_request(factor)
            event.accept()
            return
        # Plain wheel = 1 deg/step, Shift+wheel = 10 deg/step (spec S6 leaves the
        # rotate interaction to implementer discretion).
        step_deg = 10.0 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1.0
        direction = 1.0 if event.delta() > 0 else -1.0
        self.setRotation(self.rotation() + direction * step_deg)
        if self._on_commit:
            self._on_commit(self)
        event.accept()
