"""Spec S4.4 pre-flight report: shown before placement begins. Every discovered
recording appears, with its status spelled out (never a silent skip).
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout

from alignment_tool.core.discovery import (
    STATUS_MISSING,
    STATUS_PRESENT,
    STATUS_SUSPECTED_MISSPELLING,
    STATUS_UNREADABLE,
    DiscoveredRecording,
)

_STATUS_LABELS = {
    STATUS_PRESENT: "Present & readable",
    STATUS_MISSING: "Missing",
    STATUS_SUSPECTED_MISSPELLING: "Suspected misspelling",
    STATUS_UNREADABLE: "Present but unreadable",
}


class PreflightDialog(QDialog):
    def __init__(self, discovered: list[DiscoveredRecording], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pre-flight report")
        self.resize(560, 400)

        layout = QVBoxLayout(self)
        n_present = sum(1 for d in discovered if d.status == STATUS_PRESENT)
        layout.addWidget(
            QLabel(f"{n_present} of {len(discovered)} recordings have a readable flat image.")
        )

        table = QTableWidget(len(discovered), 3)
        table.setHorizontalHeaderLabels(["Recording", "Status", "Detail"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for row, d in enumerate(discovered):
            detail = ""
            if d.status == STATUS_PRESENT and d.flat_image_path is not None:
                detail = d.flat_image_path.name
            elif d.status == STATUS_SUSPECTED_MISSPELLING and d.suggested_filename:
                detail = f"did you mean '{d.suggested_filename}'?"
            elif d.status == STATUS_UNREADABLE and d.flat_image_path is not None:
                detail = d.flat_image_path.name
            table.setItem(row, 0, QTableWidgetItem(d.full_id))
            table.setItem(row, 1, QTableWidgetItem(_STATUS_LABELS.get(d.status, d.status)))
            table.setItem(row, 2, QTableWidgetItem(detail))
        table.resizeColumnsToContents()
        layout.addWidget(table)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
