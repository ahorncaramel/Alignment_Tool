"""A draggable scale-bar annotation on the IHC canvas. Purely a visual aid for
judging distances by eye (e.g. against the recording's "harp string" spacing)
-- it is not part of the transform model and is not exported; it exists only
in the current view.
"""

from __future__ import annotations

from PySide6.QtCore import QLineF
from PySide6.QtGui import QColor, QFont, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsLineItem,
    QGraphicsSimpleTextItem,
)

_COLOR = QColor("yellow")


class ScaleBarItem(QGraphicsItemGroup):
    def __init__(self, length_px: float, label_text: str, parent=None):
        super().__init__(parent)

        pen = QPen(_COLOR)
        pen.setWidth(3)
        pen.setCosmetic(True)  # constant screen-pixel stroke width at any zoom

        tick_height = max(length_px * 0.15, 4.0)

        main_line = QGraphicsLineItem(QLineF(0, 0, length_px, 0))
        main_line.setPen(pen)
        self.addToGroup(main_line)

        left_tick = QGraphicsLineItem(QLineF(0, -tick_height / 2, 0, tick_height / 2))
        left_tick.setPen(pen)
        self.addToGroup(left_tick)

        right_tick = QGraphicsLineItem(QLineF(length_px, -tick_height / 2, length_px, tick_height / 2))
        right_tick.setPen(pen)
        self.addToGroup(right_tick)

        label = QGraphicsSimpleTextItem(label_text)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        label.setFont(font)
        label.setBrush(_COLOR)
        # Constant, readable screen size regardless of zoom -- this is a one-off
        # annotation, not something resized interactively after creation.
        label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        label.setPos(length_px / 2 - label.boundingRect().width() / 2, tick_height / 2 + 4)
        self.addToGroup(label)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(2000)  # always on top of everything else
