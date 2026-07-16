"""Mirrors the input Processing/OP_*/Ex_* tree under a separate output root.

Spec S12: tool output (session store, versions, CSV, action log) must go to a
location wholly separate from the input folders, which stay read-only.
"""

from __future__ import annotations

from pathlib import Path

AUTOSAVE_FILENAME = "session_autosave.json"
VERSIONS_DIRNAME = "versions"
EXPORT_CSV_FILENAME = "transform_export.csv"
ACTION_LOG_FILENAME = "action_log.txt"


def experiment_output_dir(output_root: Path, processing_root: Path, experiment_folder: Path) -> Path:
    """e.g. output_root=D:/Output, processing_root=C:/Processing,
    experiment_folder=C:/Processing/OP_006/Ex_006_03
    -> D:/Output/OP_006/Ex_006_03
    """
    processing_root = Path(processing_root).resolve()
    experiment_folder = Path(experiment_folder).resolve()
    try:
        relative = experiment_folder.relative_to(processing_root)
    except ValueError as exc:
        raise ValueError(
            f"experiment folder {experiment_folder} is not under processing root {processing_root}"
        ) from exc
    return Path(output_root) / relative


def autosave_path(output_root: Path, processing_root: Path, experiment_folder: Path) -> Path:
    return experiment_output_dir(output_root, processing_root, experiment_folder) / AUTOSAVE_FILENAME


def versions_dir(output_root: Path, processing_root: Path, experiment_folder: Path) -> Path:
    return experiment_output_dir(output_root, processing_root, experiment_folder) / VERSIONS_DIRNAME


def export_csv_path(output_root: Path, processing_root: Path, experiment_folder: Path) -> Path:
    return experiment_output_dir(output_root, processing_root, experiment_folder) / EXPORT_CSV_FILENAME


def action_log_path(output_root: Path, processing_root: Path, experiment_folder: Path) -> Path:
    return experiment_output_dir(output_root, processing_root, experiment_folder) / ACTION_LOG_FILENAME
