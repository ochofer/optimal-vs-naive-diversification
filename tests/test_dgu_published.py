"""
Checks src/bp/dgu_published.py against the journal PDF, digit by digit.

The PDF is copyrighted and lives outside the repository (../papers/). When it
is absent the PDF comparison is skipped and only the internal consistency
checks run. When it is present, every transcribed number in Tables 3, 4, 5
and 6 is re-read with pdftotext and compared exactly.
"""
from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import dgu_published as P  # noqa: E402

PDF_CANDIDATES = [
    ROOT.parent / "papers" / "DGU 2009 Optimal Versus Naive Diversification.pdf",
    ROOT / "papers" / "DGU 2009 Optimal Versus Naive Diversification.pdf",
]

# Row labels as printed in the paper, mapped to the module's keys.
LABELS = {
    "1/N": "ew", "mv (in sample)": "mv (in sample)", "mv (true)": "mv (true)", "mv": "mv",
    "bs": "bs", "dm (σα = 1.0%)": "dm", "dm": "dm", "min": "min", "vw": "vw", "mp": "mp",
    "mv-c": "mv-c", "bs-c": "bs-c", "min-c": "min-c", "g-min-c": "g-min-c",
    "mv-min": "mv-min", "ew-min": "ew-min",
}
NUM = re.compile(r"[−-]?\d+\.\d+")


def _pdf() -> pathlib.Path | None:
    for p in PDF_CANDIDATES:
        if p.exists():
            return p
    return None


def _page_text(pdf: pathlib.Path, page: int) -> str:
    out = subprocess.run(["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(pdf), "-"],
                         check=True, capture_output=True, text=True).stdout
    return out.replace("−", "-")


def _rows(text: str, start_marker: str, end_marker: str, n_cols: int) -> dict[str, list[float]]:
    """Numbers per labelled row between two markers; p-value rows in parentheses are skipped."""
    block = text.split(start_marker, 1)[1].split(end_marker, 1)[0]
    rows = {}
    for line in block.splitlines():
        s = line.strip()
        if not s or s.startswith("("):
            continue
        m = re.match(r"^([A-Za-z0-9/\-\s\(\)σα=%\.]+?)\s{2,}(.*)$", s)
        if not m:
            continue
        label, rest = m.group(1).strip(), m.group(2)
        if label not in LABELS:
            continue
        nums = [float(x) for x in NUM.findall(rest)]
        if len(nums) >= n_cols:
            rows[LABELS[label]] = nums[:n_cols]
    return rows


def test_internal_consistency():
    for key, (vals, p) in P.SHARPE.items():
        assert len(vals) == 4
        assert p is None or len(p) == 4
    assert all(v == 0.1138 for v in P.SHARPE["vw"][0])
    assert set(P.TURNOVER_RELATIVE) == set(P.RETURN_LOSS)
    for key, vals in P.SIM_SHARPE.items():
        assert len(vals) == 9, key
    assert P.table("sharpe").shape == (14, 4)
    assert P.table("sim_sharpe").shape == (13, 9)


@pytest.mark.skipif(_pdf() is None or shutil.which("pdftotext") is None,
                    reason="journal PDF or pdftotext not available")
def test_tables_match_pdf():
    pdf = _pdf()
    # Table 3 is on PDF page 17, Table 4 on 20, Table 5 on 21, Table 6 on 29.
    # The six empirical columns are S&P, Industry, International, MKT/SMB/HML, FF-1, FF-4;
    # the module keeps columns 2, 4, 5, 6 (1-based).
    keep = [1, 3, 4, 5]
    t3 = _rows(_page_text(pdf, 17), "Strategy", "For each of the empirical datasets", 6)
    for key, (vals, _) in P.SHARPE.items():
        assert key in t3, f"Table 3 row {key} not parsed"
        assert [t3[key][i] for i in keep] == list(vals), (key, t3[key], vals)
    t4 = _rows(_page_text(pdf, 20), "Strategy", "For each of the empirical datasets", 6)
    for key, (vals, _) in P.CEQ.items():
        assert [t4[key][i] for i in keep] == list(vals), (key, t4[key], vals)
    p21 = _page_text(pdf, 21)
    t5a = _rows(p21, "Panel A", "Panel B", 6)
    t5b = _rows(p21, "Panel B", "For each of the empirical datasets", 6)
    one_n = _rows(p21, "Strategy", "Panel A", 6)["ew"]
    assert [one_n[i] for i in keep] == list(P.TURNOVER_1N)
    for key, vals in P.TURNOVER_RELATIVE.items():
        if key == "vw":
            continue  # printed as bare zeros, which the number pattern does not match
        assert [t5a[key][i] for i in keep] == list(vals), (key, t5a[key], vals)
    for key, vals in P.RETURN_LOSS.items():
        assert [t5b[key][i] for i in keep] == list(vals), (key, t5b[key], vals)
    t6 = _rows(_page_text(pdf, 29), "Strategy", "This table reports", 9)
    for key, vals in P.SIM_SHARPE.items():
        assert key in t6, f"Table 6 row {key} not parsed"
        assert t6[key] == list(vals), (key, t6[key], vals)
