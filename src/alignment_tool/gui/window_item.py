"""One calcium-recording flat-image window: draggable, rotatable, independently
faded, non-destructively contrast-adjusted. Position/rotation/scale here must
stay in the same convention as core/transform.py: item-local origin (0,0) is
the image CENTRE (spec: x/y refer to the window centre).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem, QGraphicsRectItem

from alignment_tool.core.session import STATE_NO, STATE_UNDECIDED, STATE_YES
from alignment_tool.gui.image_loading import array_to_qpixmap, load_image_array
from alignment_tool.gui.label_item import make_label

# Colours for the activity outline (spec conversation: green = activity seen,
# red = no activity, no outline = undecided). Kept in one place and mirrored
# in core/composite.py's _ACTIVITY_OUTLINE_COLOR for the exported PNG -- if
# you change one, change the other.
_ACTIVITY_OUTLINE_PENS = {
    STATE_YES: QColor(40, 200, 40),
    STATE_NO: QColor(220, 40, 40),
}

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
        parent=None,
    ):
        super().__init__(parent)
        self.full_id = full_id
        self.short_number = short_number
        self.image_path = Path(image_path)
        # Fired once per discrete user action (drag release), NOT on every
        # intermediate mouse-move -- otherwise a single drag would flood the
        # undo stack with one entry per pixel of motion.
        self._on_commit = on_commit
        self._display_min: float | None = None
        self._display_max: float | None = None

        self._array = load_image_array(self.image_path)
        self.native_height_px, self.native_width_px = self._array.shape[:2]

        self._refresh_pixmap()

        # Alignment lock (spec conversation): while locked, placement (drag/
        # rotate/scale) is frozen -- the deliberate "I am done aligning" gate
        # that also unblinds activity/cyp11b2 marking in the side panel. The
        # item stays selectable either way, so it can still be picked to view/
        # set its activity or cyp11b2 state while locked.
        self._locked = False
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

        # Activity outline: an unfilled border around the window, green for
        # "activity seen", red for "no activity", hidden while undecided (the
        # default -- must never come up already coloured). This is a separate,
        # independently-set judgement made after alignment (spec conversation:
        # align first, unbiased; mark activity afterwards); it is not tied to
        # placement or to dropped/transparency state. cyp11b2_state (below) is
        # deliberately given NO on-screen treatment here.
        self._activity_state = STATE_UNDECIDED
        self._activity_outline = QGraphicsRectItem(self.boundingRect(), self)
        self._activity_outline.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        # Cosmetic: pen stays a constant width on screen regardless of the
        # item's own scale/rotation (batch scale can be as small as ~0.05,
        # where a non-cosmetic pen width would be invisible or huge).
        outline_pen = QPen(QColor(0, 0, 0))
        outline_pen.setWidth(4)
        outline_pen.setCosmetic(True)
        self._activity_outline.setPen(outline_pen)
        self._activity_outline.setZValue(3)  # above the dropped tint, below the label (z=1000)
        self._activity_outline.setVisible(False)

        # cyp11b2_state: stored only, per the spec conversation -- the user is
        # not yet sure how to visualise it, and drawing anything for it now
        # would bias the (separate, blinded) act of judging it. Do not add a
        # visual cue here without an explicit decision to do so.
        self._cyp11b2_state = STATE_UNDECIDED

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

    def set_locked(self, locked: bool) -> None:
        """Gate interactive drag placement without touching programmatic edits
        -- set_placement()/set_scale()/set_theta_deg() are also called from
        main_window when *restoring* a session (including a locked one), so
        they must keep working regardless of this flag. Selectability is
        deliberately left alone: a locked window must still be selectable so
        its activity/cyp11b2 state can be set from the side panel.
        """
        self._locked = locked
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not locked)

    def is_locked(self) -> bool:
        return self._locked

    def set_activity_state(self, state: str) -> None:
        if state not in (STATE_UNDECIDED, STATE_YES, STATE_NO):
            raise ValueError(f"invalid activity_state: {state!r}")
        self._activity_state = state
        color = _ACTIVITY_OUTLINE_PENS.get(state)
        if color is None:
            self._activity_outline.setVisible(False)
            return
        pen = self._activity_outline.pen()
        pen.setColor(color)
        self._activity_outline.setPen(pen)
        self._activity_outline.setVisible(True)

    def activity_state(self) -> str:
        return self._activity_state

    def set_cyp11b2_state(self, state: str) -> None:
        # No visual effect by design (see __init__ note) -- purely round-trips
        # through commit/session/export.
        if state not in (STATE_UNDECIDED, STATE_YES, STATE_NO):
            raise ValueError(f"invalid cyp11b2_state: {state!r}")
        self._cyp11b2_state = state

    def cyp11b2_state(self) -> str:
        return self._cyp11b2_state

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
