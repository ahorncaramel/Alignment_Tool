import pytest

from alignment_tool.core.paths import (
    action_log_path,
    autosave_path,
    experiment_output_dir,
    export_csv_path,
    versions_dir,
)


def test_experiment_output_dir_mirrors_the_relative_structure(tmp_path):
    processing_root = tmp_path / "Processing"
    experiment_folder = processing_root / "OP_006" / "Ex_006_03"
    experiment_folder.mkdir(parents=True)
    output_root = tmp_path / "Output"

    result = experiment_output_dir(output_root, processing_root, experiment_folder)
    assert result == output_root / "OP_006" / "Ex_006_03"


def test_derived_paths_all_live_under_the_mirrored_experiment_dir(tmp_path):
    processing_root = tmp_path / "Processing"
    experiment_folder = processing_root / "OP_006" / "Ex_006_03"
    experiment_folder.mkdir(parents=True)
    output_root = tmp_path / "Output"
    expected_base = output_root / "OP_006" / "Ex_006_03"

    assert autosave_path(output_root, processing_root, experiment_folder) == expected_base / "session_autosave.json"
    assert versions_dir(output_root, processing_root, experiment_folder) == expected_base / "versions"
    assert export_csv_path(output_root, processing_root, experiment_folder) == expected_base / "transform_export.csv"
    assert action_log_path(output_root, processing_root, experiment_folder) == expected_base / "action_log.txt"


def test_raises_if_experiment_folder_is_not_under_processing_root(tmp_path):
    processing_root = tmp_path / "Processing"
    processing_root.mkdir()
    unrelated_folder = tmp_path / "SomewhereElse" / "Ex_006_03"
    unrelated_folder.mkdir(parents=True)
    output_root = tmp_path / "Output"

    with pytest.raises(ValueError):
        experiment_output_dir(output_root, processing_root, unrelated_folder)
