import pytest

from alignment_tool.core.session import (
    ContrastSettings,
    PixelSize,
    PreflightEntry,
    RecordingState,
    SessionHistory,
    SessionState,
    from_dict,
    load_session_json,
    save_session_json,
    to_dict,
)
from alignment_tool.core.transform import SimilarityPlacement


def make_session(scale=1.0) -> SessionState:
    return SessionState(
        experiment_id="Ex_006_03",
        experiment_folder="C:/Processing/OP_006/Ex_006_03",
        processing_root="C:/Processing",
        ihc_image_path="C:/Processing/OP_006/Ex_006_03/ihc.jpg",
        ihc_transparency_step=0,
        shared_scale=scale,
        scale_source="manual",
        pixel_size_flat=PixelSize(value_um_per_px=None, source="none"),
        pixel_size_ihc=PixelSize(value_um_per_px=None, source="none"),
        recordings=[
            RecordingState(
                full_id="Rec_006_03_01",
                short_number=1,
                flat_image_path="C:/Processing/OP_006/Ex_006_03/Rec_006_03_01/Flatrec_Rec_006_03_01.tif",
                width_px=512,
                height_px=512,
                placement=SimilarityPlacement(theta_deg=12.0, x=100.0, y=200.0),
                transparency_step=2,
                contrast=ContrastSettings(display_min=10.0, display_max=200.0),
            ),
            RecordingState(
                full_id="Rec_006_03_02",
                short_number=2,
                flat_image_path="C:/Processing/OP_006/Ex_006_03/Rec_006_03_02/Flatrec_Rec_006_03_02.tif",
                width_px=512,
                height_px=512,
                placement=SimilarityPlacement(theta_deg=0.0, x=0.0, y=0.0),
            ),
        ],
        preflight_report=[
            PreflightEntry(full_id="Rec_006_03_01", status="present", matched_filename="Flatrec_Rec_006_03_01.tif"),
            PreflightEntry(full_id="Rec_006_03_02", status="present", matched_filename="Flatrec_Rec_006_03_02.tif"),
        ],
        created_at="2026-07-15T12:00:00",
        last_modified="2026-07-15T12:00:00",
    )


def test_to_dict_from_dict_round_trip_is_exact():
    session = make_session()
    restored = from_dict(to_dict(session))
    assert restored == session


def test_json_save_load_round_trip_reproduces_placements_exactly(tmp_path):
    session = make_session()
    path = tmp_path / "session_autosave.json"
    save_session_json(session, path)
    restored = load_session_json(path)
    assert restored == session
    assert restored.recordings[0].placement == session.recordings[0].placement


def test_save_is_atomic_no_leftover_tmp_file(tmp_path):
    session = make_session()
    path = tmp_path / "session_autosave.json"
    save_session_json(session, path)
    assert path.exists()
    assert not (tmp_path / "session_autosave.json.tmp").exists()


def test_undo_floor_is_the_load_point_snapshot():
    session = make_session(scale=1.0)
    history = SessionHistory(session)
    assert not history.can_undo()

    edited = from_dict(to_dict(session))
    edited.shared_scale = 2.0
    history.apply(edited)
    assert history.current.shared_scale == 2.0
    assert history.can_undo()

    restored = history.undo()
    assert restored.shared_scale == 1.0
    assert not history.can_undo()
    with pytest.raises(IndexError):
        history.undo()


def test_redo_restores_the_undone_edit_and_clears_on_new_edit():
    session = make_session(scale=1.0)
    history = SessionHistory(session)

    step1 = from_dict(to_dict(session))
    step1.shared_scale = 2.0
    history.apply(step1)

    history.undo()
    assert history.can_redo()
    restored = history.redo()
    assert restored.shared_scale == 2.0
    assert not history.can_redo()

    # a fresh edit after undo must clear the (now irrelevant) redo stack
    history.undo()
    step2 = from_dict(to_dict(history.current))
    step2.shared_scale = 3.0
    history.apply(step2)
    assert not history.can_redo()
