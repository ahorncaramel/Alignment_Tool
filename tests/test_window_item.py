from PIL import Image

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
