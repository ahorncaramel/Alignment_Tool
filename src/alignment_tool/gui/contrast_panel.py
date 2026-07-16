"""Spec S8.2: non-destructive display-only min/max range for whichever flat
image is currently selected. Never touches the source file or its pixel data.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QPushButton, QVBoxLayout, QWidget


class ContrastPanel(QWidget):
    contrastEdited = Signal(float, float)  # display_min, display_max

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_range = (0.0, 255.0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        form = QFormLayout()

        self._min_spin = QDoubleSpinBox()
        self._min_spin.setRange(0, 65535)
        self._max_spin = QDoubleSpinBox()
        self._max_spin.setRange(0, 65535)
        self._max_spin.setValue(255)
        self._min_spin.valueChanged.connect(self._emit)
        self._max_spin.valueChanged.connect(self._emit)
        form.addRow("Display min:", self._min_spin)
        form.addRow("Display max:", self._max_spin)
        layout.addLayout(form)

        reset_btn = QPushButton("Reset to full range")
        reset_btn.clicked.connect(self.reset_to_full_range)
        layout.addWidget(reset_btn)

    def _emit(self) -> None:
        self.contrastEdited.emit(self._min_spin.value(), self._max_spin.value())

    def set_range(self, display_min: float, display_max: float, *, full_range: tuple[float, float]) -> None:
        self._full_range = full_range
        self._min_spin.blockSignals(True)
        self._max_spin.blockSignals(True)
        self._min_spin.setValue(display_min)
        self._max_spin.setValue(display_max)
        self._min_spin.blockSignals(False)
        self._max_spin.blockSignals(False)

    def reset_to_full_range(self) -> None:
        self.set_range(*self._full_range, full_range=self._full_range)
        self._emit()
