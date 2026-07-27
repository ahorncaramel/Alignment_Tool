"""A draggable, resizable ruler annotation on the IHC canvas: a straight line
marked off in equal divisions (default 5 x 1000 um = 5000 um). Meant to be
dragged onto the image and stretched (via its end handle, or the control
panel's length field) to match an existing embedded scale bar, then used to
eyeball a recording window's harp spacing against the division marks while
adjusting the batch scale. Purely a visual aid -- not part of the transform
model, and not exported or persisted.

Deliberately NOT given ItemIgnoresTransformations anywhere (unlike the window
number label in label_item.py): this tool only means anything if it scales
exactly like the IHC image as the user zooms, so a 1000 um division always
covers the same real image pixels regardless of zoom level.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QLineF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsSceneMouseEvent,
    QGraphicsSimpleTextItem,
)

_COLOR = QColor("dodgerblue")
_MIN_LENGTH_PX = 10.0


class RulerItem(QGraphicsItemGroup):
    def __init__(
        self,
        length_px: float,
        total_um: float,
        division_um: float,
        on_length_changed: Callable[[float], None] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._total_um = total_um
        self._division_um = division_um
        self._num_divisions = max(1, round(total_um / division_um))
        self._length_px = max(_MIN_LENGTH_PX, length_px)
        self._on_length_changed = on_length_changed

        pen = QPen(_COLOR)
        pen.setWidth(2)
        pen.setCosmetic(True)  # constant screen-pixel stroke width at any zoom

        self._main_line = QGraphicsLineItem()
        self._main_line.setPen(pen)
        self.addToGroup(self._main_line)

        self._ticks: list[QGraphicsLineItem] = []
        for _ in range(self._num_divisions + 1):
            tick = QGraphicsLineItem()
            tick.setPen(pen)
            self.addToGroup(tick)
            self._ticks.append(tick)

        self._label = QGraphicsSimpleTextItem()
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self._label.setFont(font)
        self._label.setBrush(_COLOR)
        self.addToGroup(self._label)

        self._handle = _ResizeHandle(self)
        self.addToGroup(self._handle)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(2000)  # always on top of everything else

        self._layout()

    def set_length_px(self, length_px: float) -> None:
        self._length_px = max(_MIN_LENGTH_PX, length_px)
        self._layout()
        if self._on_length_changed:
            self._on_length_changed(self._length_px)

    def length_px(self) -> float:
        return self._length_px

    def num_divisions(self) -> int:
        return self._num_divisions

    def _layout(self) -> None:
        length = self._length_px
        tick_height = max(length * 0.06, 6.0)

        self._main_line.setLine(QLineF(0, 0, length, 0))
        step = length / self._num_divisions
        for i, tick in enumerate(self._ticks):
            x = i * step
            tick.setLine(QLineF(x, -tick_height / 2, x, tick_height / 2))

        self._label.setText(
            f"{self._total_um:g} µm ({self._num_divisions} x {self._division_um:g} µm)"
        )
        self._label.setPos(length / 2 - self._label.boundingRect().width() / 2, tick_height / 2 + 4)

        # Keep the handle at the movable end regardless of layout changes.
        self._handle.setPos(length, 0)


class _ResizeHandle(QGraphicsRectItem):
    """Drag this to stretch the ruler's on-screen length. Its represented
    micrometre value stays fixed -- this is purely for matching pixel length
    against a physical reference (e.g. a bar baked into the IHC image), not
    for re-calibrating the ruler's own um value.
    """

    def __init__(self, ruler: RulerItem):
        super().__init__(-5, -5, 10, 10)
        self._ruler = ruler
        self.setBrush(QBrush(_COLOR))
        self.setPen(QPen(_COLOR))
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setZValue(1)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        local = self._ruler.mapFromScene(event.scenePos())
        self._ruler.set_length_px(local.x())
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        event.accept()
