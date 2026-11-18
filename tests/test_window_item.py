import pytest
from PIL import Image
from PySide6.QtWidgets import QGraphicsItem

from alignment_tool.core.session import STATE_NO, STATE_UNDECIDED, STATE_YES
from alignment_tool.gui.window_item import RecordingWindowItem


def _make_flat_image(path):
    Image.new("L", (64, 48)).save(path)


def test_set_scale_leaves_label_at_a_constant_readable_size(qapp, tmp_path):
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    item.set_scale(0.055)
    assert item.scale() == 0.055
    assert item._label.scale() == 1.0

    item.set_scale(3.0)
    assert item.scale() == 3.0
    assert item._label.scale() == 1.0


def test_set_placement_leaves_label_at_a_constant_readable_size(qapp, tmp_path):
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    item.set_placement(theta_deg=10.0, x=5.0, y=6.0, scale=0.05)
    assert item.scale() == 0.05
    assert item._label.scale() == 1.0


def test_set_theta_deg_matches_theta_deg_getter(qapp, tmp_path):
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    item.set_theta_deg(37.5)
    assert item.theta_deg() == 37.5


def test_dropped_marker_toggles_without_hiding_the_item(qapp, tmp_path):
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    assert item.is_dropped() is False
    assert item._dropped_overlay.isVisible() is False

    item.set_dropped(True)
    assert item.is_dropped() is True
    assert item._dropped_overlay.isVisible() is True
    assert item.isVisible()  # the window itself must stay visible/selectable

    item.set_dropped(False)
    assert item.is_dropped() is False
    assert item._dropped_overlay.isVisible() is False


def test_activity_state_defaults_to_undecided_with_no_outline(qapp, tmp_path):
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    assert item.activity_state() == STATE_UNDECIDED
    assert item._activity_outline.isVisible() is False


def test_activity_state_yes_shows_a_visible_outline(qapp, tmp_path):
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    item.set_activity_state(STATE_YES)
    assert item.activity_state() == STATE_YES
    assert item._activity_outline.isVisible() is True


def test_activity_state_no_shows_a_visible_outline(qapp, tmp_path):
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    item.set_activity_state(STATE_NO)
    assert item.activity_state() == STATE_NO
    assert item._activity_outline.isVisible() is True


def test_activity_state_back_to_undecided_hides_the_outline_again(qapp, tmp_path):
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    item.set_activity_state(STATE_YES)
    item.set_activity_state(STATE_UNDECIDED)
    assert item._activity_outline.isVisible() is False


def test_activity_state_rejects_unknown_values(qapp, tmp_path):
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    with pytest.raises(ValueError):
        item.set_activity_state("maybe")


def test_cyp11b2_state_round_trips_without_any_visual_effect(qapp, tmp_path):
    """Spec conversation: cyp11b2_state must stay purely data, no on-screen cue,
    so a blinded judgement of it is never biased by something already drawn."""
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    assert item.cyp11b2_state() == STATE_UNDECIDED
    item.set_cyp11b2_state(STATE_YES)
    assert item.cyp11b2_state() == STATE_YES
    # No outline/overlay item is toggled by this -- only the dropped overlay
    # and activity outline exist as visual items, and neither reacts to this.
    assert item._dropped_overlay.isVisible() is False
    assert item._activity_outline.isVisible() is False


def test_cyp11b2_state_rejects_unknown_values(qapp, tmp_path):
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    with pytest.raises(ValueError):
        item.set_cyp11b2_state("maybe")


def test_unlocked_by_default_and_movable(qapp, tmp_path):
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    assert item.is_locked() is False
    assert item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable


def test_set_locked_true_clears_the_movable_flag(qapp, tmp_path):
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    item.set_locked(True)
    assert item.is_locked() is True
    assert not (item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable)


def test_set_locked_false_restores_movability(qapp, tmp_path):
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    item.set_locked(True)
    item.set_locked(False)
    assert item.is_locked() is False
    assert item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable


def test_set_placement_still_works_while_locked(qapp, tmp_path):
    """Programmatic placement (used when the GUI restores a session, including
    a locked one) must not be blocked by the lock -- only interactive edits are."""
    path = tmp_path / "Flatrec_006_03_01.png"
    _make_flat_image(path)
    item = RecordingWindowItem("Rec_006_03_01", 1, path)

    item.set_locked(True)
    item.set_placement(theta_deg=15.0, x=10.0, y=20.0, scale=0.5)
    assert item.theta_deg() == 15.0
    assert item.scale() == 0.5
