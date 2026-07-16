from PIL import Image

from alignment_tool.core.discovery import (
    STATUS_MISSING,
    STATUS_PRESENT,
    STATUS_SUSPECTED_MISSPELLING,
    STATUS_UNREADABLE,
    build_initial_recordings,
    find_experiments,
    scan_experiment,
    to_preflight_entries,
)


def _make_rec_folder(root, full_id):
    folder = root / full_id
    folder.mkdir()
    return folder


def _write_valid_png(path):
    Image.new("L", (8, 8)).save(path)


def test_all_four_preflight_states_are_distinguished(tmp_path):
    experiment = tmp_path / "Ex_006_03"
    experiment.mkdir()

    present = _make_rec_folder(experiment, "Rec_006_03_01")
    _write_valid_png(present / "Flatrec_Rec_006_03_01.png")

    missing = _make_rec_folder(experiment, "Rec_006_03_02")
    (missing / "unrelated_notes.txt").write_text("no flat image here")

    misspelled = _make_rec_folder(experiment, "Rec_006_03_03")
    _write_valid_png(misspelled / "Flatrec_Rec_006_03_3.png")  # missing leading zero

    unreadable = _make_rec_folder(experiment, "Rec_006_03_04")
    (unreadable / "Flatrec_Rec_006_03_04.png").write_bytes(b"not actually a png")

    results = {r.full_id: r for r in scan_experiment(experiment)}

    assert results["Rec_006_03_01"].status == STATUS_PRESENT
    assert results["Rec_006_03_01"].flat_image_path.name == "Flatrec_Rec_006_03_01.png"

    assert results["Rec_006_03_02"].status == STATUS_MISSING

    assert results["Rec_006_03_03"].status == STATUS_SUSPECTED_MISSPELLING
    assert results["Rec_006_03_03"].suggested_filename == "Flatrec_Rec_006_03_3.png"

    assert results["Rec_006_03_04"].status == STATUS_UNREADABLE


def test_no_recording_is_silently_dropped(tmp_path):
    experiment = tmp_path / "Ex_006_03"
    experiment.mkdir()
    for i in range(1, 4):
        folder = _make_rec_folder(experiment, f"Rec_006_03_0{i}")
        if i != 2:
            _write_valid_png(folder / f"Flatrec_Rec_006_03_0{i}.png")

    results = scan_experiment(experiment)
    assert {r.full_id for r in results} == {"Rec_006_03_01", "Rec_006_03_02", "Rec_006_03_03"}
    assert all(r.status is not None for r in results)


def test_results_are_sorted_by_recording_number(tmp_path):
    experiment = tmp_path / "Ex_006_03"
    experiment.mkdir()
    for i in [3, 1, 2]:
        folder = _make_rec_folder(experiment, f"Rec_006_03_0{i}")
        _write_valid_png(folder / f"Flatrec_Rec_006_03_0{i}.png")

    results = scan_experiment(experiment)
    assert [r.short_number for r in results] == [1, 2, 3]


def test_non_recording_folders_are_ignored(tmp_path):
    experiment = tmp_path / "Ex_006_03"
    experiment.mkdir()
    (experiment / "notes").mkdir()
    (experiment / "README.txt").write_text("hi")
    rec = _make_rec_folder(experiment, "Rec_006_03_01")
    _write_valid_png(rec / "Flatrec_Rec_006_03_01.png")

    results = scan_experiment(experiment)
    assert len(results) == 1
    assert results[0].full_id == "Rec_006_03_01"


def test_build_initial_recordings_includes_every_discovered_recording_unplaced(tmp_path):
    experiment = tmp_path / "Ex_006_03"
    experiment.mkdir()
    present = _make_rec_folder(experiment, "Rec_006_03_01")
    _write_valid_png(present / "Flatrec_Rec_006_03_01.png")
    missing = _make_rec_folder(experiment, "Rec_006_03_02")
    (missing / "notes.txt").write_text("no image")

    discovered = scan_experiment(experiment)
    recordings = build_initial_recordings(discovered)

    by_id = {r.full_id: r for r in recordings}
    assert by_id["Rec_006_03_01"].placement is None
    assert by_id["Rec_006_03_01"].dropped is False
    assert by_id["Rec_006_03_01"].width_px == 8
    assert by_id["Rec_006_03_01"].height_px == 8
    assert by_id["Rec_006_03_02"].placement is None
    assert by_id["Rec_006_03_02"].width_px is None
    assert by_id["Rec_006_03_02"].flat_image_path is None


def test_to_preflight_entries_mirrors_discovery_status(tmp_path):
    experiment = tmp_path / "Ex_006_03"
    experiment.mkdir()
    misspelled = _make_rec_folder(experiment, "Rec_006_03_01")
    _write_valid_png(misspelled / "Flatrec_Rec_006_03_1.png")

    discovered = scan_experiment(experiment)
    entries = to_preflight_entries(discovered)

    assert len(entries) == 1
    assert entries[0].full_id == "Rec_006_03_01"
    assert entries[0].status == STATUS_SUSPECTED_MISSPELLING
    assert entries[0].suggested_filename == "Flatrec_Rec_006_03_1.png"


def test_find_experiments_scans_op_and_ex_folders(tmp_path):
    processing_root = tmp_path / "Processing"
    (processing_root / "OP_006" / "Ex_006_03").mkdir(parents=True)
    (processing_root / "OP_006" / "Ex_006_04").mkdir(parents=True)
    (processing_root / "OP_007" / "Ex_007_01").mkdir(parents=True)
    (processing_root / "OP_006" / "not_an_experiment").mkdir(parents=True)
    (processing_root / "not_a_surgery").mkdir(parents=True)

    experiments = find_experiments(processing_root)
    assert [e[0] for e in experiments] == ["Ex_006_03", "Ex_006_04", "Ex_007_01"]


def test_find_experiments_returns_empty_for_missing_root(tmp_path):
    assert find_experiments(tmp_path / "does_not_exist") == []
