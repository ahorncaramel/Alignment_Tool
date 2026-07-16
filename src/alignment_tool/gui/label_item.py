"""Spec S7: the short-number label is a working tool, not decoration. It must
stay attached to its window through drag/rotate/scale, yet stay crisp and
un-rotated on top regardless of the window's opacity or rotation.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import QGraphicsItem, QGraphicsSimpleTextItem


def make_label(parent_item: QGraphicsItem, text: str) -> QGraphicsSimpleTextItem:
    label = QGraphicsSimpleTextItem(text, parent_item)
    font = QFont()
    font.setPointSize(14)
    font.setBold(True)
    label.setFont(font)
    label.setBrush(QBrush(QColor("yellow")))
    # Ignoring the parent's transform keeps the label upright and constant-size
    # regardless of the window's rotation/scale; ignoring parent opacity keeps
    # it fully opaque no matter how faded the window is (spec S7, S9).
    label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
    label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresParentOpacity, True)
    label.setZValue(1000)
    label.setPos(-label.boundingRect().width() / 2, -label.boundingRect().height() / 2)
    return label
