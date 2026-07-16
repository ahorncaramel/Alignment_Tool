"""Spec S5.3: the single shared batch-scale control. Numeric entry is the
authoritative view; drag-to-resize (handled by the scene) updates the same
value through set_scale() so the two are always in agreement.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QWidget


class ScalePanel(QWidget):
    scaleEdited = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Batch scale:"))

        self._spin = QDoubleSpinBox()
        self._spin.setRange(0.0001, 1000.0)
        self._spin.setDecimals(4)
        self._spin.setSingleStep(0.01)
        self._spin.valueChanged.connect(self.scaleEdited.emit)
        layout.addWidget(self._spin)

        self._source_label = QLabel("")
        layout.addWidget(self._source_label)
        layout.addStretch()

    def set_scale(self, value: float, *, source: str) -> None:
        self._spin.blockSignals(True)
        self._spin.setValue(value)
        self._spin.blockSignals(False)
        self._source_label.setText(f"({source})")

    def value(self) -> float:
        return self._spin.value()
