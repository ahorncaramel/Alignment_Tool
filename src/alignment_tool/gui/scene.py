"""The layered composite (spec S9): IHC (z=0) below windows (z=1) below labels
(z=1000+, handled by each window item itself). A plain QGraphicsScene already
respects item z-values, so the "explicit z-order" requirement is satisfied by
each item declaring its own zValue at construction, held in one place (here)
rather than left to insertion order.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView


class AlignmentScene(QGraphicsScene):
    pass


class AlignmentView(QGraphicsView):
    def __init__(self, scene: AlignmentScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(self.renderHints())
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def wheelEvent(self, event) -> None:
        # Ctrl+wheel zooms the view; plain wheel is forwarded (default QGraphicsView
        # behaviour) to whichever item is under the cursor, so a window item's own
        # wheelEvent (rotation) still fires normally.
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)
