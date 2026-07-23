import numpy as np
import tifffile

from alignment_tool.gui.image_loading import array_to_qpixmap, load_image_array


def test_plain_2d_tiff_loads_unchanged(tmp_path):
    path = tmp_path / "flat.tif"
    tifffile.imwrite(str(path), np.full((48, 64), 100, dtype=np.uint8))

    arr = load_image_array(path)
    assert arr.shape == (48, 64)


def test_ome_tiff_singleton_axes_are_squeezed(tmp_path):
    """tifffile commonly returns OME-TIFF data with singleton T/Z/C axes even
    for a single-plane image, e.g. shape (1, 1, 1, H, W). This must not crash
    and must produce a plain 2D array -- this is exactly what a real Micro-
    Manager / OMERO OME-TIFF flat image looks like.
    """
    path = tmp_path / "flat_ome.tif"
    data = np.full((1, 1, 1, 48, 64), 100, dtype=np.uint16)
    tifffile.imwrite(str(path), data)

    arr = load_image_array(path)
    assert arr.ndim == 2
    assert arr.shape == (48, 64)


def test_rgb_tiff_is_averaged_to_grayscale(tmp_path):
    path = tmp_path / "flat_rgb.tif"
    data = np.zeros((48, 64, 3), dtype=np.uint8)
    data[..., 0] = 100
    data[..., 1] = 150
    data[..., 2] = 200
    tifffile.imwrite(str(path), data, photometric="rgb")

    arr = load_image_array(path)
    assert arr.shape == (48, 64)
    assert arr[0, 0] == 150.0  # mean(100, 150, 200)


def test_non_tiff_grayscale_png_loads_unchanged(tmp_path):
    from PIL import Image

    path = tmp_path / "flat.png"
    Image.new("L", (64, 48), color=120).save(path)

    arr = load_image_array(path)
    assert arr.shape == (48, 64)


def test_unexpected_stack_dimension_falls_back_to_first_plane_instead_of_crashing(tmp_path):
    """Not a documented flat-image shape (spec S4.3 expects an already-averaged
    single plane), but if one somehow appears, this must degrade gracefully
    rather than raise -- a wrong-but-visible image beats a hard crash while
    the user is trying to align.
    """
    path = tmp_path / "stack.tif"
    data = np.stack([np.full((48, 64), i, dtype=np.uint8) for i in range(5)])  # (5, 48, 64)
    tifffile.imwrite(str(path), data)

    arr = load_image_array(path)
    assert arr.shape == (48, 64)


def test_array_to_qpixmap_produces_correctly_sized_pixmap(qapp):
    arr = np.full((48, 64), 100.0)
    pixmap = array_to_qpixmap(arr, None, None)
    assert pixmap.width() == 64
    assert pixmap.height() == 48
