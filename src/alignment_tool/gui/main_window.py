"""Top-level window: wires the experiment picker, pre-flight report, IHC
selection, the graphics scene, side-panel controls, and persistence/export
together. This module is intentionally the "glue" layer -- all the logic it
calls into (transform math, discovery, session model, export) lives in
core/ and is independently tested there.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from alignment_tool.core import export, paths
from alignment_tool.core.discovery import (
    build_initial_recordings,
    read_image_dimensions,
    scan_experiment,
    to_preflight_entries,
)
from alignment_tool.core.metadata import compute_prefill_scale, read_pixel_size_um
from alignment_tool.core.session import (
    ContrastSettings,
    PixelSize,
    RecordingState,
    SessionHistory,
    SessionState,
    load_session_json,
    save_session_json,
)
from alignment_tool.core.transform import SimilarityPlacement
from alignment_tool.gui.contrast_panel import ContrastPanel
from alignment_tool.gui.experiment_picker import ExperimentPickerDialog
from alignment_tool.gui.ihc_item import IhcLayerItem
from alignment_tool.gui.ihc_select_dialog import IhcSelectDialog
from alignment_tool.gui.preflight_dialog import PreflightDialog
from alignment_tool.gui.scale_panel import ScalePanel
from alignment_tool.gui.scene import AlignmentScene, AlignmentView
from alignment_tool.gui.window_item import RecordingWindowItem

_AUTOSAVE_DEBOUNCE_MS = 500


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alignment Tool")
        self.resize(1200, 800)

        self._processing_root: Path | None = None
        self._output_root: Path | None = None
        self._experiment_folder: Path | None = None
        self._history: SessionHistory | None = None
        self._window_items: dict[str, RecordingWindowItem] = {}
        self._ihc_item: IhcLayerItem | None = None
        self._selected_item: RecordingWindowItem | None = None

        self._scene = AlignmentScene(self)
        self._scene.selectionChanged.connect(self._on_selection_changed)
        self._view = AlignmentView(self._scene, self)
        self.setCentralWidget(self._view)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._do_autosave)

        self._build_menu()
        self._build_side_panel()
        self.statusBar().showMessage("No experiment open")

        QTimer.singleShot(0, self.open_experiment_flow)

    # ---- UI scaffolding -------------------------------------------------

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        open_action = QAction("&Open Experiment...", self)
        open_action.triggered.connect(self.open_experiment_flow)
        file_menu.addAction(open_action)

        save_as_action = QAction("Save &As Version...", self)
        save_as_action.triggered.connect(self._save_as)
        file_menu.addAction(save_as_action)

        export_action = QAction("&Export Transform CSV...", self)
        export_action.triggered.connect(self._export)
        file_menu.addAction(export_action)

        edit_menu = self.menuBar().addMenu("&Edit")
        self._undo_action = QAction("&Undo", self)
        self._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self._undo_action.triggered.connect(self._undo)
        edit_menu.addAction(self._undo_action)

        self._redo_action = QAction("&Redo", self)
        self._redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self._redo_action.triggered.connect(self._redo)
        edit_menu.addAction(self._redo_action)

    def _build_side_panel(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self._scale_panel = ScalePanel()
        self._scale_panel.scaleEdited.connect(self._on_scale_edited)
        layout.addWidget(self._scale_panel)

        layout.addWidget(QLabel("IHC transparency (0=opaque, 9=90% transparent):"))
        self._ihc_transparency_spin = QSpinBox()
        self._ihc_transparency_spin.setRange(0, 9)
        self._ihc_transparency_spin.valueChanged.connect(self._on_ihc_transparency_changed)
        layout.addWidget(self._ihc_transparency_spin)

        layout.addWidget(QLabel("Selected window transparency:"))
        self._window_transparency_spin = QSpinBox()
        self._window_transparency_spin.setRange(0, 9)
        self._window_transparency_spin.setEnabled(False)
        self._window_transparency_spin.valueChanged.connect(self._on_window_transparency_changed)
        layout.addWidget(self._window_transparency_spin)

        layout.addWidget(QLabel("Selected window display contrast:"))
        self._contrast_panel = ContrastPanel()
        self._contrast_panel.setEnabled(False)
        self._contrast_panel.contrastEdited.connect(self._on_contrast_edited)
        layout.addWidget(self._contrast_panel)

        self._selection_label = QLabel("No window selected")
        layout.addWidget(self._selection_label)

        self._drop_button = QPushButton("Drop selected recording")
        self._drop_button.setEnabled(False)
        self._drop_button.clicked.connect(self._drop_selected_recording)
        layout.addWidget(self._drop_button)

        layout.addStretch()

        dock = QDockWidget("Controls", self)
        dock.setWidget(panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    # ---- Experiment open flow --------------------------------------------

    def open_experiment_flow(self) -> None:
        dialog = ExperimentPickerDialog(self)
        if dialog.exec() != ExperimentPickerDialog.DialogCode.Accepted:
            return
        self._processing_root = Path(dialog.processing_root)
        self._output_root = Path(dialog.output_root)
        self._experiment_folder = Path(dialog.selected_experiment_folder)

        discovered = scan_experiment(self._experiment_folder)
        PreflightDialog(discovered, self).exec()

        autosave_path = paths.autosave_path(self._output_root, self._processing_root, self._experiment_folder)
        state: SessionState
        if autosave_path.exists():
            choice = QMessageBox.question(
                self,
                "Resume session?",
                f"A previous session was found for {self._experiment_folder.name}.\n"
                "Resume it, or start fresh (discarding it)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if choice == QMessageBox.StandardButton.Yes:
                state = load_session_json(autosave_path)
            else:
                state = self._build_fresh_session(discovered)
        else:
            state = self._build_fresh_session(discovered)

        self._history = SessionHistory(state)
        self._rebuild_scene_from_state(state)
        self.statusBar().showMessage(f"Opened {self._experiment_folder.name}")

    def _build_fresh_session(self, discovered) -> SessionState:
        ihc_dialog = IhcSelectDialog(self._experiment_folder.name, parent=self)
        if ihc_dialog.exec() != IhcSelectDialog.DialogCode.Accepted:
            raise RuntimeError("An IHC image is required to start a session.")
        ihc_path = Path(ihc_dialog.selected_path)

        recordings = build_initial_recordings(discovered)
        preflight_report = to_preflight_entries(discovered)

        pixel_size_ihc_value = read_pixel_size_um(ihc_path)
        first_present = next((r for r in recordings if r.flat_image_path), None)
        pixel_size_flat_value = (
            read_pixel_size_um(Path(first_present.flat_image_path)) if first_present else None
        )
        prefill_scale = compute_prefill_scale(pixel_size_flat_value, pixel_size_ihc_value)

        # Initial on-screen layout: stack windows in a column beside the IHC image
        # (spec S7) -- this is part of the load-time snapshot, not a user edit.
        ihc_dims = read_image_dimensions(ihc_path)
        x_cursor = (ihc_dims[0] if ihc_dims else 0) + 80
        y_cursor = 0
        scale = prefill_scale if prefill_scale is not None else 1.0
        for rec in recordings:
            if rec.width_px is None or rec.height_px is None:
                continue
            cx = x_cursor + (rec.width_px * scale) / 2.0
            cy = y_cursor + (rec.height_px * scale) / 2.0
            rec.placement = SimilarityPlacement(theta_deg=0.0, x=cx, y=cy)
            y_cursor += rec.height_px * scale + 20

        now = _now_iso()
        return SessionState(
            experiment_id=self._experiment_folder.name,
            experiment_folder=str(self._experiment_folder),
            processing_root=str(self._processing_root),
            ihc_image_path=str(ihc_path),
            ihc_transparency_step=0,
            shared_scale=scale,
            scale_source="metadata" if prefill_scale is not None else "manual",
            pixel_size_flat=PixelSize(
                value_um_per_px=pixel_size_flat_value,
                source="metadata" if pixel_size_flat_value is not None else "none",
            ),
            pixel_size_ihc=PixelSize(
                value_um_per_px=pixel_size_ihc_value,
                source="metadata" if pixel_size_ihc_value is not None else "none",
            ),
            recordings=recordings,
            preflight_report=preflight_report,
            created_at=now,
            last_modified=now,
        )

    # ---- Scene <-> SessionState -------------------------------------------

    def _rebuild_scene_from_state(self, state: SessionState) -> None:
        self._scene.clear()
        self._window_items.clear()
        self._selected_item = None

        self._ihc_item = IhcLayerItem(Path(state.ihc_image_path))
        self._ihc_item.set_transparency_step(state.ihc_transparency_step)
        self._scene.addItem(self._ihc_item)

        for rec in state.recordings:
            if rec.dropped or rec.placement is None or not rec.flat_image_path:
                continue
            item = RecordingWindowItem(
                rec.full_id,
                rec.short_number,
                Path(rec.flat_image_path),
                on_commit=self._on_window_commit,
                on_scale_request=self._on_scale_request,
            )
            item.set_placement(rec.placement.theta_deg, rec.placement.x, rec.placement.y, state.shared_scale)
            item.set_transparency_step(rec.transparency_step)
            item.set_contrast(rec.contrast.display_min, rec.contrast.display_max)
            self._scene.addItem(item)
            self._window_items[rec.full_id] = item

        self._scale_panel.set_scale(state.shared_scale, source=state.scale_source)
        self._ihc_transparency_spin.blockSignals(True)
        self._ihc_transparency_spin.setValue(state.ihc_transparency_step)
        self._ihc_transparency_spin.blockSignals(False)
        self._update_undo_redo_actions()
        # Any previously-selected item was just destroyed by scene.clear() above;
        # explicitly resync the side panel to "nothing selected" rather than
        # leaving it showing a now-dangling item's stale values.
        self._on_selection_changed()

    def _build_current_session_state(self) -> SessionState:
        base = self._history.current
        recordings = []
        for rec in base.recordings:
            item = self._window_items.get(rec.full_id)
            if item is None:
                recordings.append(rec)
                continue
            theta = item.theta_deg()
            pos = item.pos()
            display_min, display_max = item.contrast()
            recordings.append(
                RecordingState(
                    full_id=rec.full_id,
                    short_number=rec.short_number,
                    flat_image_path=rec.flat_image_path,
                    width_px=rec.width_px,
                    height_px=rec.height_px,
                    placement=SimilarityPlacement(theta_deg=theta, x=pos.x(), y=pos.y()),
                    dropped=rec.dropped,
                    transparency_step=item.transparency_step(),
                    contrast=ContrastSettings(display_min=display_min, display_max=display_max),
                )
            )
        return SessionState(
            experiment_id=base.experiment_id,
            experiment_folder=base.experiment_folder,
            processing_root=base.processing_root,
            ihc_image_path=base.ihc_image_path,
            ihc_transparency_step=self._ihc_transparency_spin.value(),
            shared_scale=self._scale_panel.value(),
            scale_source=base.scale_source,
            pixel_size_flat=base.pixel_size_flat,
            pixel_size_ihc=base.pixel_size_ihc,
            recordings=recordings,
            preflight_report=base.preflight_report,
            created_at=base.created_at,
            last_modified=_now_iso(),
        )

    def _commit(self) -> None:
        if self._history is None:
            return
        new_state = self._build_current_session_state()
        self._history.apply(new_state)
        self._update_undo_redo_actions()
        self._autosave_timer.start(_AUTOSAVE_DEBOUNCE_MS)

    def _do_autosave(self) -> None:
        if self._history is None:
            return
        path = paths.autosave_path(self._output_root, self._processing_root, self._experiment_folder)
        save_session_json(self._history.current, path)

    def _update_undo_redo_actions(self) -> None:
        if self._history is None:
            self._undo_action.setEnabled(False)
            self._redo_action.setEnabled(False)
            return
        self._undo_action.setEnabled(self._history.can_undo())
        self._redo_action.setEnabled(self._history.can_redo())

    # ---- Item-driven commits ----------------------------------------------

    def _on_window_commit(self, item: RecordingWindowItem) -> None:
        self._commit()

    def _on_scale_request(self, factor: float) -> None:
        new_scale = self._scale_panel.value() * factor
        self._scale_panel.set_scale(new_scale, source="manual")
        for item in self._window_items.values():
            item.setScale(new_scale)
        self._commit()

    def _on_scale_edited(self, value: float) -> None:
        for item in self._window_items.values():
            item.setScale(value)
        self._commit()

    def _on_ihc_transparency_changed(self, step: int) -> None:
        if self._ihc_item:
            self._ihc_item.set_transparency_step(step)
        self._commit()

    def _on_window_transparency_changed(self, step: int) -> None:
        if self._selected_item:
            self._selected_item.set_transparency_step(step)
            self._commit()

    def _on_contrast_edited(self, display_min: float, display_max: float) -> None:
        if self._selected_item:
            self._selected_item.set_contrast(display_min, display_max)
            self._commit()

    def _on_selection_changed(self) -> None:
        selected = [i for i in self._scene.selectedItems() if isinstance(i, RecordingWindowItem)]
        self._selected_item = selected[0] if selected else None
        has_selection = self._selected_item is not None
        self._window_transparency_spin.setEnabled(has_selection)
        self._contrast_panel.setEnabled(has_selection)
        self._drop_button.setEnabled(has_selection)
        if has_selection:
            item = self._selected_item
            self._selection_label.setText(f"Selected: {item.full_id}")
            self._window_transparency_spin.blockSignals(True)
            self._window_transparency_spin.setValue(
                round((1.0 - item.opacity()) / 0.1)
            )
            self._window_transparency_spin.blockSignals(False)
            lo, hi = float(item._array.min()), float(item._array.max())
            display_min, display_max = item.contrast()
            self._contrast_panel.set_range(
                display_min if display_min is not None else lo,
                display_max if display_max is not None else hi,
                full_range=(lo, hi),
            )
        else:
            self._selection_label.setText("No window selected")

    def _drop_selected_recording(self) -> None:
        """Explicit user decision to exclude a recording (spec: independent of
        the pre-flight image status -- an otherwise-placeable recording can
        still be deliberately left out). Recorded as status "dropped" in the
        export, distinct from "missing"/"unreadable" (core/export.py).
        """
        if self._history is None or self._selected_item is None:
            return
        full_id = self._selected_item.full_id
        self._scene.removeItem(self._selected_item)
        del self._window_items[full_id]
        self._selected_item = None

        base = self._history.current
        recordings = [
            replace(rec, dropped=True) if rec.full_id == full_id else rec for rec in base.recordings
        ]
        new_state = replace(base, recordings=recordings, last_modified=_now_iso())
        self._history.apply(new_state)
        self._update_undo_redo_actions()
        self._autosave_timer.start(_AUTOSAVE_DEBOUNCE_MS)
        self._on_selection_changed()

    # ---- Undo / redo --------------------------------------------------------

    def _undo(self) -> None:
        if self._history and self._history.can_undo():
            state = self._history.undo()
            self._rebuild_scene_from_state(state)
            self._autosave_timer.start(_AUTOSAVE_DEBOUNCE_MS)

    def _redo(self) -> None:
        if self._history and self._history.can_redo():
            state = self._history.redo()
            self._rebuild_scene_from_state(state)
            self._autosave_timer.start(_AUTOSAVE_DEBOUNCE_MS)

    # ---- Save As / Export ---------------------------------------------------

    def _save_as(self) -> None:
        if self._history is None:
            return
        name, ok = QInputDialog.getText(self, "Save As Version", "Version name:")
        if not ok or not name:
            return
        timestamp = _now_iso().replace(":", "-")
        version_path = (
            paths.versions_dir(self._output_root, self._processing_root, self._experiment_folder)
            / f"{name}_{timestamp}.json"
        )
        save_session_json(self._history.current, version_path)
        QMessageBox.information(self, "Saved", f"Saved version to {version_path}")

    def _export(self) -> None:
        if self._history is None:
            return
        timestamp = _now_iso()
        csv_path = paths.export_csv_path(self._output_root, self._processing_root, self._experiment_folder)
        log_path = paths.action_log_path(self._output_root, self._processing_root, self._experiment_folder)
        export.write_transform_csv(self._history.current, csv_path)
        export.write_action_log(self._history.current, log_path, timestamp)
        QMessageBox.information(self, "Exported", f"Wrote:\n{csv_path}\n{log_path}")
