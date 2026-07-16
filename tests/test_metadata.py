import numpy as np
import pytest
import tifffile

from alignment_tool.core.metadata import compute_prefill_scale, read_pixel_size_um

_OME_XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06">
  <Image ID="Image:0">
    <Pixels ID="Pixels:0" DimensionOrder="XYCZT" Type="uint8"
            SizeX="8" SizeY="8" SizeC="1" SizeZ="1" SizeT="1"
            PhysicalSizeX="{size}" PhysicalSizeXUnit="{unit}"
            PhysicalSizeY="{size}" PhysicalSizeYUnit="{unit}">
    </Pixels>
  </Image>
</OME>
"""


def _write_ome_tiff(path, size=0.65, unit="µm"):
    data = np.zeros((8, 8), dtype=np.uint8)
    xml = _OME_XML_TEMPLATE.format(size=size, unit=unit)
    tifffile.imwrite(str(path), data, description=xml, metadata=None)


def test_reads_physical_size_x_in_micrometres(tmp_path):
    # "um" (ASCII) rather than "µm": tifffile enforces 7-bit ASCII when writing a
    # fresh ImageDescription tag. Real OME-TIFF files may carry non-ASCII bytes for
    # this unit, which is a pure-read path unaffected by that write-side restriction.
    path = tmp_path / "flat.tif"
    _write_ome_tiff(path, size=0.65, unit="um")
    assert read_pixel_size_um(path) == 0.65


def test_converts_non_micrometre_units(tmp_path):
    path = tmp_path / "flat_nm.tif"
    _write_ome_tiff(path, size=650.0, unit="nm")
    assert read_pixel_size_um(path) == pytest.approx(0.65)


def test_returns_none_for_non_tiff_formats(tmp_path):
    from PIL import Image

    path = tmp_path / "flat.png"
    Image.new("L", (8, 8)).save(path)
    assert read_pixel_size_um(path) is None


def test_returns_none_for_tiff_without_ome_metadata(tmp_path):
    path = tmp_path / "plain.tif"
    tifffile.imwrite(str(path), np.zeros((8, 8), dtype=np.uint8))
    assert read_pixel_size_um(path) is None


def test_compute_prefill_scale_requires_both_sides():
    assert compute_prefill_scale(0.65, 0.25) == pytest.approx(0.65 / 0.25)
    assert compute_prefill_scale(None, 0.25) is None
    assert compute_prefill_scale(0.65, None) is None
