"""
Ken French data library: download, record, parse.

The library serves each dataset as a zip holding one CSV. The CSV is not a
single table. It is a text file with between two and ten blocks, each announced by a title
line ("  Average Value Weighted Returns -- Monthly"), followed by a header row
that starts with a comma, followed by rows that start with a date: six digits
for monthly data (192607), four for annual (1927). Missing values are coded
-99.99 or -999. Returns are in percent.

This module turns that into pandas DataFrames indexed by a monthly Period, in
decimal returns, with the missing codes replaced by NaN. It also writes a
provenance record for every file it downloads: the URL, the download time, the
SHA-256 of the zip, and the CRSP vintage line French prints at the top of each
CSV. A result is only as reproducible as the vintage it was computed on, and
French revises history, so the record is part of every output.

Nothing here is committed to the repository: the zips live in a local cache
directory that .gitignore excludes.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

from . import constants as C

_DATE_ROW = re.compile(r"^\s*(\d{8}|\d{6}|\d{4})\s*,")   # daily YYYYMMDD, monthly YYYYMM, annual YYYY


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download(key: str, cache_dir: str | Path = "data/french", force: bool = False) -> dict:
    """Fetch one French zip by its key in constants.FRENCH_FILES.

    Returns the provenance record for the file and writes the zip to cache_dir.
    A cached zip is reused unless force=True, and its record is rebuilt from the
    cached bytes, so the SHA-256 always describes the file actually on disk.
    """
    filename = C.FRENCH_FILES[key]
    url = C.FRENCH_BASE_URL + filename
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / filename
    if force or not path.exists():
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        path.write_bytes(response.content)
        fetched_now = True
    else:
        fetched_now = False
    data = path.read_bytes()
    now_utc = datetime.now(timezone.utc)
    record = {
        "key": key,
        "filename": filename,
        "url": url,
        "fetched_this_run": fetched_now,
        "download_time_utc": now_utc.isoformat(timespec="seconds"),
        "download_time_local": now_utc.astimezone(ZoneInfo(C.TIMEZONE)).isoformat(timespec="seconds"),
        "zip_sha256": sha256_bytes(data),
        "zip_bytes": len(data),
        "vintage_line": _vintage_line(data),
    }
    return record


def _csv_text(zip_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"expected one CSV in the zip, found {names}")
        return zf.read(names[0]).decode("latin-1")


def _vintage_line(zip_bytes: bytes) -> str:
    """The first line of the CSV, e.g. 'This file was created using the 202607 CRSP database.'"""
    text = _csv_text(zip_bytes)
    for line in text.splitlines():
        if line.strip():
            first = line.strip()
            return first.split(".")[0] + "." if "." in first else first
    return ""


def parse_blocks(text: str) -> list[dict]:
    """Split a French CSV into its blocks.

    Each block is returned as {"title": str, "frequency": "daily" | "monthly" |
    "annual", "frame": DataFrame} where the frame is indexed by Period (day,
    month or year) and holds floats in the file's own units (percent). The title is the last non-empty line before
    the header row that is not itself a data row.
    """
    lines = text.splitlines()
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        if _DATE_ROW.match(lines[i]):
            # Walk back to the header row (starts with a comma) and the title above it.
            header_idx = i - 1
            while header_idx >= 0 and not lines[header_idx].lstrip().startswith(","):
                header_idx -= 1
            if header_idx < 0:
                raise ValueError(f"data row at line {i} has no header row above it")
            title_idx = header_idx - 1
            while title_idx >= 0 and not lines[title_idx].strip():
                title_idx -= 1
            title = lines[title_idx].strip() if title_idx >= 0 else ""
            # The factor files and the later blocks of the size-and-value file
            # carry no title line, only prose; a sentence is not a title.
            if not title or title.endswith(".") or len(title) > 70:
                title = f"(untitled block {len(blocks)})"
            columns = [c.strip() for c in lines[header_idx].split(",")[1:]]
            rows = []
            j = i
            while j < n and _DATE_ROW.match(lines[j]):
                rows.append(lines[j])
                j += 1
            raw = pd.read_csv(io.StringIO("\n".join(rows)), header=None, index_col=0)
            raw.columns = columns[: raw.shape[1]]
            date_len = len(str(raw.index[0]).strip())
            if date_len == 8:
                idx = pd.PeriodIndex(pd.to_datetime(raw.index.astype(str), format="%Y%m%d"), freq="D")
                freq = "daily"
            elif date_len == 6:
                idx = pd.PeriodIndex([pd.Period(f"{str(d)[:4]}-{str(d)[4:6]}", freq="M") for d in raw.index])
                freq = "monthly"
            else:
                idx = pd.PeriodIndex([pd.Period(str(d), freq="Y") for d in raw.index])
                freq = "annual"
            frame = raw.astype(float)
            frame.index = idx
            frame.index.name = "period"
            blocks.append({"title": title, "frequency": freq, "frame": frame})
            i = j
        else:
            i += 1
    return blocks


def load_blocks(key: str, cache_dir: str | Path = "data/french") -> list[dict]:
    """All blocks of one file, with the file's provenance record attached to each."""
    record = download(key, cache_dir)
    text = _csv_text((Path(cache_dir) / C.FRENCH_FILES[key]).read_bytes())
    blocks = parse_blocks(text)
    for b in blocks:
        b["provenance"] = record
    return blocks


def load_monthly(key: str, block: int | str = 0, cache_dir: str | Path = "data/french",
                 as_decimal: bool = True) -> pd.DataFrame:
    """One block of one file, in decimal returns with missing codes as NaN.

    The name dates from the monthly files; the function serves the daily files
    in the same way (the block's index is then a daily Period).

    block is an integer position among the file's blocks, or a regular
    expression matched against block titles (the first match wins).
    """
    blocks = load_blocks(key, cache_dir)
    if isinstance(block, int):
        chosen = blocks[block]
    else:
        matches = [b for b in blocks if re.search(block, b["title"], flags=re.I)]
        if not matches:
            raise KeyError(f"no block in {key} matches {block!r}; titles: {[b['title'] for b in blocks]}")
        chosen = matches[0]
    frame = chosen["frame"].copy()
    for code in C.FRENCH_MISSING_CODES:
        frame = frame.mask(np.isclose(frame, code))
    if as_decimal and C.FRENCH_RETURNS_ARE_PERCENT:
        frame = frame / 100.0
    frame.attrs["title"] = chosen["title"]
    frame.attrs["provenance"] = chosen["provenance"]
    return frame


def load_counts(key: str, block: int | str, cache_dir: str | Path = "data/french") -> pd.DataFrame:
    """A block in the file's own units (firm counts, average firm size), missing codes as NaN."""
    return load_monthly(key, block, cache_dir, as_decimal=False)


def write_provenance(records: list[dict], path: str | Path = C.PROVENANCE_FILE) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records, key=lambda r: r["key"])
    path.write_text(json.dumps(ordered, indent=2, sort_keys=True) + "\n")
    return path


def block_summary(key: str, cache_dir: str | Path = "data/french") -> pd.DataFrame:
    """One row per block: title, frequency, columns, rows, first and last period."""
    rows = []
    for k, b in enumerate(load_blocks(key, cache_dir)):
        f = b["frame"]
        rows.append({
            "file": key, "block": k, "title": b["title"], "frequency": b["frequency"],
            "columns": f.shape[1], "rows": f.shape[0],
            "first": str(f.index[0]), "last": str(f.index[-1]),
        })
    return pd.DataFrame(rows)
