import math

import pytest

from alignment_tool.core.transform import (
    SimilarityPlacement,
    ihc_to_window,
    window_to_ihc,
)


def test_centre_maps_to_placement_xy_regardless_of_rotation_or_scale():
    window_size = (100.0, 60.0)
    placement = SimilarityPlacement(theta_deg=37.0, x=250.0, y=-40.0)
    centre = (50.0, 30.0)
    result = window_to_ihc(centre, window_size, scale=2.5, placement=placement)
    assert result == pytest.approx((250.0, -40.0))


def test_no_rotation_no_scale_is_a_pure_translation():
    window_size = (100.0, 60.0)
    placement = SimilarityPlacement(theta_deg=0.0, x=10.0, y=20.0)
    # top-left corner of the window is (-50, -30) relative to its centre
    result = window_to_ihc((0.0, 0.0), window_size, scale=1.0, placement=placement)
    assert result == pytest.approx((10.0 - 50.0, 20.0 - 30.0))


def test_scale_is_applied_around_the_centre():
    window_size = (100.0, 60.0)
    placement = SimilarityPlacement(theta_deg=0.0, x=0.0, y=0.0)
    result = window_to_ihc((100.0, 30.0), window_size, scale=2.0, placement=placement)
    # local point is (50, 0) relative to centre -> scaled to (100, 0)
    assert result == pytest.approx((100.0, 0.0))


def test_positive_rotation_is_visually_counter_clockwise():
    """A point to the right of centre, rotated +90 deg, should end up above
    centre (i.e. smaller y, since y is down) -- this pins down the sign
    convention documented in transform.py and relied on by the CSV export.
    """
    window_size = (2.0, 2.0)  # centre at (1, 1)
    placement = SimilarityPlacement(theta_deg=90.0, x=0.0, y=0.0)
    result = window_to_ihc((2.0, 1.0), window_size, scale=1.0, placement=placement)
    assert result == pytest.approx((0.0, -1.0), abs=1e-9)


@pytest.mark.parametrize(
    "theta_deg,scale,x,y",
    [
        (0.0, 1.0, 0.0, 0.0),
        (37.0, 2.5, 250.0, -40.0),
        (-123.0, 0.75, -10.0, 60.0),
        (180.0, 1.3, 5.0, 5.0),
    ],
)
def test_window_to_ihc_and_back_round_trips(theta_deg, scale, x, y):
    window_size = (80.0, 45.0)
    placement = SimilarityPlacement(theta_deg=theta_deg, x=x, y=y)
    local_point = (12.0, 33.0)
    ihc_point = window_to_ihc(local_point, window_size, scale, placement)
    back = ihc_to_window(ihc_point, window_size, scale, placement)
    assert back == pytest.approx(local_point)


def test_deterministic_same_inputs_same_outputs():
    window_size = (100.0, 60.0)
    placement = SimilarityPlacement(theta_deg=15.0, x=5.0, y=5.0)
    a = window_to_ihc((10.0, 10.0), window_size, 1.2, placement)
    b = window_to_ihc((10.0, 10.0), window_size, 1.2, placement)
    assert a == b
