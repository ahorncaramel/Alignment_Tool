"""Spec S4.2: a required, explicit step where the user identifies the IHC image
for the experiment being worked on. The choice is a recorded fact (the caller
logs it), not an invisible default.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QLabel, QPushButton, QVBoxLayout


class IhcSelectDialog(QDialog):
    def __init__(self, experiment_id: str, initial_path: str | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select IHC image")
        self.selected_path: str | None = initial_path

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Select the IHC image for {experiment_id}:"))

        self._path_label = QLabel(self.selected_path or "(none selected)")
        layout.addWidget(self._path_label)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        layout.addWidget(browse_btn)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_ok)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select IHC image",
            "",
            "Images (*.jpg *.jpeg *.png *.tif *.tiff *.bmp)",
        )
        if path:
            self.selected_path = path
            self._path_label.setText(path)

    def _on_ok(self) -> None:
        if self.selected_path:
            self.accept()
