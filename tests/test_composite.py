import numpy as np
import pytest
from PIL import Image

from alignment_tool.core.composite import _affine_ihc_to_window, render_aligned_composite, write_aligned_composite_png
from alignment_tool.core.session import ContrastSettings, PixelSize, PreflightEntry, RecordingState, SessionState
from alignment_tool.core.transform import SimilarityPlacement, ihc_to_window


@pytest.mark.parametrize("theta_deg,scale,px,py", [
    (0.0, 1.0, 0.0, 0.0),
    (30.0, 0.5, 100.0, 50.0),
    (-75.0, 2.2, -40.0, 300.0),
    (200.0, 0.055, 512.3, -12.7),
])
def test_affine_coefficients_match_ihc_to_window(theta_deg, scale, px, py):
    """The composite's per-pixel affine map must agree exactly with the
    already-tested transform.ihc_to_window() -- this is the one thing that
    must never silently drift (a wrong sign here mirrors/misplaces every
    exported image).
    """
    win_w, win_h = 64, 48
    placement = SimilarityPlacement(theta_deg=theta_deg, x=px, y=py)
    a, b, c, d, e, f = _affine_ihc_to_window(theta_deg, scale, px, py, win_w, win_h)

    for ihc_point in [(px, py), (px + 10, py - 5), (0.0, 0.0), (px + 37.5, py + 12.25)]:
        expected = ihc_to_window(ihc_point, (win_w, win_h), scale, placement)
        got = (a * ihc_point[0] + b * ihc_point[1] + c, d * ihc_point[0] + e * ihc_point[1] + f)
        assert got[0] == pytest.approx(expected[0], abs=1e-9)
        assert got[1] == pytest.approx(expected[1], abs=1e-9)


def _make_session(tmp_path, *, theta_deg=0.0, scale=1.0, x=100.0, y=100.0, dropped=False, placement=True):
    ihc_path = tmp_path / "ihc.png"
    Image.new("L", (300, 200), color=40).save(ihc_path)

    flat_path = tmp_path / "flat.png"
    flat = np.zeros((48, 64), dtype=np.uint8)
    flat[10:38, 10:54] = 220  # a bright rectangle so the pasted patch is checkable
    Image.fromarray(flat).save(flat_path)

    return SessionState(
        experiment_id="Ex_test",
        experiment_folder=str(tmp_path),
        processing_root=str(tmp_path),
        ihc_image_path=str(ihc_path),
        ihc_transparency_step=0,
        shared_scale=scale,
        scale_source="manual",
        pixel_size_flat=PixelSize(None, "none"),
        pixel_size_ihc=PixelSize(None, "none"),
        recordings=[
            RecordingState(
                full_id="Rec_test_01",
                short_number=1,
                flat_image_path=str(flat_path),
                width_px=64,
                height_px=48,
                placement=SimilarityPlacement(theta_deg=theta_deg, x=x, y=y) if placement else None,
                dropped=dropped,
                transparency_step=0,
                contrast=ContrastSettings(),
            )
        ],
        preflight_report=[PreflightEntry(full_id="Rec_test_01", status="present", matched_filename="flat.png")],
        created_at="2026-01-01T00:00:00",
        last_modified="2026-01-01T00:00:00",
    )


def test_composite_is_sized_to_the_ihc_image(tmp_path):
    session = _make_session(tmp_path)
    image = render_aligned_composite(session)
    assert image.size == (300, 200)


def test_window_pixels_land_at_the_expected_ihc_location_unrotated(tmp_path):
    session = _make_session(tmp_path, theta_deg=0.0, scale=1.0, x=150.0, y=100.0)
    image = render_aligned_composite(session)
    arr = np.array(image.convert("L"))
    # The window's centre (bright square) should be bright at its placement.
    assert arr[100, 150] > 150
    # A background IHC-only point should not be affected by the window.
    assert arr[10, 10] < 150


def test_dropped_and_unplaced_recordings_are_skipped_without_crashing(tmp_path):
    dropped_session = _make_session(tmp_path, dropped=True)
    unplaced_session = _make_session(tmp_path, placement=False)
    render_aligned_composite(dropped_session)
    render_aligned_composite(unplaced_session)  # must not raise


def test_write_aligned_composite_png_writes_a_readable_png(tmp_path):
    session = _make_session(tmp_path)
    out_path = tmp_path / "out" / "aligned.png"
    write_aligned_composite_png(session, out_path)
    assert out_path.exists()
    with Image.open(out_path) as img:
        assert img.format == "PNG"
        assert img.size == (300, 200)
