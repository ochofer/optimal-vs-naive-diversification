"""Parser checks on a fixture shaped like a French CSV, with no network."""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import french_loader as fl  # noqa: E402

FIXTURE = """This file was created using the 202607 CRSP database.
It contains value- and equal-weighted returns for 3 industry portfolios.

Missing data are indicated by -99.99 or -999.


  Average Value Weighted Returns -- Monthly
,Agric,Food ,Soda
192607,   2.36,   0.09, -99.99
192608,   2.23,   2.71, -99.99
192609,  -0.50,   1.00,   3.00

  Average Value Weighted Returns -- Annual
,Agric,Food ,Soda
1927,  10.00,  11.00, -99.99

  Number of Firms in Portfolios
,Agric,Food ,Soda
192607,     12,     25,      0
192608,     12,     25,      0
192609,     12,     26,      3
"""


def test_parse_blocks_shapes_and_titles():
    blocks = fl.parse_blocks(FIXTURE)
    assert [b["title"] for b in blocks] == [
        "Average Value Weighted Returns -- Monthly",
        "Average Value Weighted Returns -- Annual",
        "Number of Firms in Portfolios",
    ]
    assert [b["frequency"] for b in blocks] == ["monthly", "annual", "monthly"]
    monthly = blocks[0]["frame"]
    assert list(monthly.columns) == ["Agric", "Food", "Soda"]
    assert str(monthly.index[0]) == "1926-07" and str(monthly.index[-1]) == "1926-09"
    assert monthly.loc["1926-09", "Agric"] == -0.50
    assert blocks[2]["frame"].loc["1926-09", "Soda"] == 3


def test_vintage_line_is_first_sentence():
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("x.csv", FIXTURE)
    assert fl._vintage_line(buf.getvalue()) == "This file was created using the 202607 CRSP database."


def test_missing_codes_become_nan_and_percent_becomes_decimal(tmp_path, monkeypatch):
    import io
    import zipfile
    from bp import constants as C
    zpath = tmp_path / C.FRENCH_FILES["ind49"]
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("49_Industry_Portfolios.csv", FIXTURE)
    frame = fl.load_monthly("ind49", 0, cache_dir=tmp_path)
    assert np.isnan(frame.loc["1926-07", "Soda"])
    assert abs(frame.loc["1926-07", "Agric"] - 0.0236) < 1e-12
    counts = fl.load_counts("ind49", "Number of Firms", cache_dir=tmp_path)
    assert counts.loc["1926-09", "Food"] == 26
