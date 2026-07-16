"""Session-start dialog: pick a Processing root once (remembered), then an
experiment from a list, plus a separate remembered output root (spec: output
must live apart from the read-only input tree).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from alignment_tool.core.discovery import find_experiments

SETTINGS_ORG = "AlignmentTool"
SETTINGS_APP = "AlignmentTool"


def get_settings() -> QSettings:
    return QSettings(SETTINGS_ORG, SETTINGS_APP)


class ExperimentPickerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Open Experiment")
        self.resize(520, 400)

        self.processing_root: str | None = None
        self.output_root: str | None = None
        self.selected_experiment_folder: Path | None = None
        self._experiments: list[tuple[str, Path]] = []

        self._settings = get_settings()
        self._build_ui()

        self.processing_root = self._settings.value("processing_root") or None
        self.output_root = self._settings.value("output_root") or None
        if not self.processing_root:
            self._choose_processing_root()
        if not self.output_root:
            self._choose_output_root()
        self._refresh_experiment_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._info_label = QLabel()
        layout.addWidget(self._info_label)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self._list)

        change_buttons = QHBoxLayout()
        change_processing_btn = QPushButton("Change Processing folder...")
        change_processing_btn.clicked.connect(self._choose_processing_root)
        change_output_btn = QPushButton("Change output folder...")
        change_output_btn.clicked.connect(self._choose_output_root)
        change_buttons.addWidget(change_processing_btn)
        change_buttons.addWidget(change_output_btn)
        layout.addLayout(change_buttons)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_open_clicked)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _choose_processing_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Processing root folder")
        if folder:
            self.processing_root = folder
            self._settings.setValue("processing_root", folder)
            self._refresh_experiment_list()

    def _choose_output_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select output folder (kept separate from your Processing data)"
        )
        if folder:
            self.output_root = folder
            self._settings.setValue("output_root", folder)
            self._update_info_label()

    def _refresh_experiment_list(self) -> None:
        self._list.clear()
        self._experiments = []
        if self.processing_root:
            self._experiments = find_experiments(Path(self.processing_root))
            for ex_id, ex_folder in self._experiments:
                self._list.addItem(f"{ex_id}    ({ex_folder})")
        self._update_info_label()

    def _update_info_label(self) -> None:
        self._info_label.setText(
            f"Processing root: {self.processing_root or '(not set)'}\n"
            f"Output root: {self.output_root or '(not set)'}"
        )

    def _on_open_clicked(self) -> None:
        row = self._list.currentRow()
        if not self.processing_root or not self.output_root or row < 0:
            QMessageBox.warning(
                self,
                "Selection required",
                "Choose a Processing root, an output folder, and an experiment before opening.",
            )
            return
        self.selected_experiment_folder = self._experiments[row][1]
        self.accept()
