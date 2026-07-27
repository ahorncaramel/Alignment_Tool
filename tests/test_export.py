import csv
import io

from alignment_tool.core.export import build_action_log, write_action_log, write_transform_csv
from alignment_tool.core.session import (
    PixelSize,
    PreflightEntry,
    RecordingState,
    SessionState,
)
from alignment_tool.core.transform import SimilarityPlacement


def make_session() -> SessionState:
    return SessionState(
        experiment_id="Ex_006_03",
        experiment_folder="C:/Processing/OP_006/Ex_006_03",
        processing_root="C:/Processing",
        ihc_image_path="C:/Processing/OP_006/Ex_006_03/ihc.jpg",
        ihc_transparency_step=0,
        shared_scale=1.75,
        scale_source="manual",
        pixel_size_flat=PixelSize(),
        pixel_size_ihc=PixelSize(),
        recordings=[
            RecordingState(
                full_id="Rec_006_03_02",
                short_number=2,
                flat_image_path="C:/Processing/OP_006/Ex_006_03/Rec_006_03_02/Flatrec_Rec_006_03_02.tif",
                width_px=256,
                height_px=256,
                placement=SimilarityPlacement(theta_deg=45.0, x=500.0, y=600.0),
            ),
            RecordingState(
                full_id="Rec_006_03_01",
                short_number=1,
                flat_image_path="C:/Processing/OP_006/Ex_006_03/Rec_006_03_01/Flatrec_Rec_006_03_01.tif",
                width_px=512,
                height_px=512,
                placement=SimilarityPlacement(theta_deg=12.0, x=100.0, y=200.0),
            ),
            RecordingState(
                full_id="Rec_006_03_03",
                short_number=3,
                flat_image_path=None,
            ),
            RecordingState(
                full_id="Rec_006_03_04",
                short_number=4,
                flat_image_path="C:/Processing/OP_006/Ex_006_03/Rec_006_03_04/Flatrec_Rec_006_03_04.tif",
                width_px=300,
                height_px=300,
                dropped=True,
            ),
        ],
        preflight_report=[
            PreflightEntry(full_id="Rec_006_03_01", status="present", matched_filename="Flatrec_Rec_006_03_01.tif"),
            PreflightEntry(full_id="Rec_006_03_02", status="present", matched_filename="Flatrec_Rec_006_03_02.tif"),
            PreflightEntry(full_id="Rec_006_03_03", status="missing"),
            PreflightEntry(full_id="Rec_006_03_04", status="present", matched_filename="Flatrec_Rec_006_03_04.tif"),
        ],
        created_at="2026-07-15T12:00:00",
        last_modified="2026-07-15T12:00:00",
    )


def _read_data_rows(csv_path):
    text = csv_path.read_text(encoding="utf-8")
    data_lines = [line for line in text.splitlines() if not line.startswith("#")]
    return list(csv.DictReader(io.StringIO("\n".join(data_lines))))


def test_csv_has_a_row_per_discovered_recording_including_unplaced_ones(tmp_path):
    session = make_session()
    path = write_transform_csv(session, tmp_path / "transform.csv")
    rows = _read_data_rows(path)
    assert {r["full_id"] for r in rows} == {
        "Rec_006_03_01",
        "Rec_006_03_02",
        "Rec_006_03_03",
        "Rec_006_03_04",
    }


def test_csv_rows_are_ordered_by_short_number(tmp_path):
    session = make_session()
    path = write_transform_csv(session, tmp_path / "transform.csv")
    rows = _read_data_rows(path)
    assert [r["full_id"] for r in rows] == [
        "Rec_006_03_01",
        "Rec_006_03_02",
        "Rec_006_03_03",
        "Rec_006_03_04",
    ]


def test_missing_recording_gets_a_placeholder_row_with_blank_transform_fields(tmp_path):
    session = make_session()
    path = write_transform_csv(session, tmp_path / "transform.csv")
    rows = {r["full_id"]: r for r in _read_data_rows(path)}
    row = rows["Rec_006_03_03"]
    assert row["status"] == "missing"
    assert row["x"] == ""
    assert row["y"] == ""
    assert row["rotation_deg"] == ""
    assert row["window_width_px"] == ""
    assert row["window_height_px"] == ""
    # scale is a session-level constant, still reported even on placeholder rows
    assert row["scale"] == "1.75"


def test_dropped_recording_gets_status_dropped_not_its_preflight_status(tmp_path):
    session = make_session()
    path = write_transform_csv(session, tmp_path / "transform.csv")
    rows = {r["full_id"]: r for r in _read_data_rows(path)}
    row = rows["Rec_006_03_04"]
    assert row["status"] == "dropped"
    assert row["x"] == ""


def test_placed_recording_gets_status_placed(tmp_path):
    session = make_session()
    path = write_transform_csv(session, tmp_path / "transform.csv")
    rows = {r["full_id"]: r for r in _read_data_rows(path)}
    assert rows["Rec_006_03_01"]["status"] == "placed"


def test_scale_is_identical_across_every_row(tmp_path):
    session = make_session()
    path = write_transform_csv(session, tmp_path / "transform.csv")
    rows = _read_data_rows(path)
    assert {r["scale"] for r in rows} == {"1.75"}


def test_csv_contains_explicit_convention_header(tmp_path):
    session = make_session()
    path = write_transform_csv(session, tmp_path / "transform.csv")
    text = path.read_text(encoding="utf-8")
    assert "origin" in text.lower()
    assert "counter-clockwise" in text.lower()
    assert "centre" in text.lower()


def test_csv_row_values_match_the_placement(tmp_path):
    session = make_session()
    path = write_transform_csv(session, tmp_path / "transform.csv")
    rows = {r["full_id"]: r for r in _read_data_rows(path)}
    row = rows["Rec_006_03_01"]
    assert row["x"] == "100.0"
    assert row["y"] == "200.0"
    assert row["rotation_deg"] == "12.0"
    assert row["window_width_px"] == "512"
    assert row["window_height_px"] == "512"


def test_csv_row_carries_the_flat_image_path_so_a_row_is_self_contained(tmp_path):
    session = make_session()
    path = write_transform_csv(session, tmp_path / "transform.csv")
    rows = {r["full_id"]: r for r in _read_data_rows(path)}
    assert rows["Rec_006_03_01"]["flat_image_path"] == (
        "C:/Processing/OP_006/Ex_006_03/Rec_006_03_01/Flatrec_Rec_006_03_01.tif"
    )
    # A recording discovery couldn't find an image for still gets a row, blank path.
    assert rows["Rec_006_03_03"]["flat_image_path"] == ""


def test_csv_references_the_aligned_image_when_given_one(tmp_path):
    session = make_session()
    path = write_transform_csv(
        session, tmp_path / "transform.csv", aligned_image_path="D:/Output/OP_006/Ex_006_03/aligned_composite.png"
    )
    text = path.read_text(encoding="utf-8")
    assert "aligned_composite.png" in text


def test_action_log_records_experiment_ihc_preflight_scale_and_timestamp():
    session = make_session()
    log = build_action_log(session, export_timestamp="2026-07-15T13:00:00")
    assert "Ex_006_03" in log
    assert "ihc.jpg" in log
    assert "1.75" in log
    assert "manual" in log
    assert "Rec_006_03_03: missing" in log
    assert "2026-07-15T13:00:00" in log


def test_write_action_log_writes_to_disk(tmp_path):
    session = make_session()
    path = write_action_log(session, tmp_path / "action_log.txt", export_timestamp="2026-07-15T13:00:00")
    assert path.exists()
    assert "Ex_006_03" in path.read_text(encoding="utf-8")
