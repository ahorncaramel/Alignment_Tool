"""Spec S4.2: a required, explicit step where the user identifies the IHC image
for the experiment being worked on. The choice is a recorded fact (the caller
logs it), not an invisible default.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout

from alignment_tool.core.discovery import read_image_dimensions
from alignment_tool.gui.experiment_picker import get_settings

# Where the real IHC exports live (as opposed to small preview copies elsewhere
# on disk) -- a sensible starting point for the file dialog until the user has
# browsed once, after which the last-used folder (see get_settings) wins.
_DEFAULT_IHC_FOLDER = r"D:\Daten Cara\Human Adrenal\IHC\IHC_29.07_3Mpx_coloured_tiff_300DPI"

# A real IHC export is a large whole-slide scan; a small preview copy (e.g.
# mislabelled "ihc_008_01.tif") is nowhere close to this on its long side.
_PREVIEW_WARNING_THRESHOLD_PX = 1000


class IhcSelectDialog(QDialog):
    def __init__(self, experiment_id: str, initial_path: str | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select IHC image")
        self.selected_path: str | None = initial_path
        self._settings = get_settings()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Select the IHC image for {experiment_id}:"))

        self._path_label = QLabel()
        layout.addWidget(self._path_label)
        self._update_path_label()

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        layout.addWidget(browse_btn)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_ok)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _update_path_label(self) -> None:
        if not self.selected_path:
            self._path_label.setText("(none selected)")
            return
        dims = read_image_dimensions(Path(self.selected_path))
        dims_text = f"{dims[0]} \u00d7 {dims[1]} px" if dims else "size unknown"
        self._path_label.setText(f"{self.selected_path}\n{dims_text}")

    def _browse(self) -> None:
        start_dir = self._settings.value("ihc_default_folder") or _DEFAULT_IHC_FOLDER
        while True:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Select IHC image",
                start_dir,
                "Images (*.jpg *.jpeg *.png *.tif *.tiff *.bmp)",
            )
            if not path:
                return

            dims = read_image_dimensions(Path(path))
            if dims is not None and max(dims) < _PREVIEW_WARNING_THRESHOLD_PX:
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Icon.Warning)
                box.setWindowTitle("This looks like a preview copy")
                box.setText(
                    f"{Path(path).name} is {dims[0]} \u00d7 {dims[1]} px, under the "
                    f"{_PREVIEW_WARNING_THRESHOLD_PX} px long-side threshold -- this looks "
                    "like a small preview copy rather than the real export."
                )
                continue_btn = box.addButton("Continue anyway", QMessageBox.ButtonRole.AcceptRole)
                choose_another_btn = box.addButton("Choose another file...", QMessageBox.ButtonRole.RejectRole)
                box.setDefaultButton(choose_another_btn)
                box.exec()
                if box.clickedButton() is choose_another_btn:
                    start_dir = str(Path(path).parent)
                    continue

            self.selected_path = path
            self._settings.setValue("ihc_default_folder", str(Path(path).parent))
            self._update_path_label()
            return

    def _on_ok(self) -> None:
        if self.selected_path:
            self.accept()
