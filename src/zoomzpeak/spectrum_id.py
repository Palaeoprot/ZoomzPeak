"""Stable spectrum identity: a readable URN plus a short content hash.

Python twin of ``zoomzpeak_schema::spectrum_id`` (Rust). The two must produce the
same id for the same spectrum; both are tested against the same reference vectors.

    {dataset}_{raw}_s{scan}_{hash6}        D20240599_ZN0_s2_03388f
    {dataset}_{raw}_r{row}_{hash6}         when a spectrum has no scan number

The hash is the first 6 lowercase hex characters of SHA-256 over, in order:

1. ``dataset`` as UTF-8, then one 0x00
2. ``raw`` as UTF-8, then one 0x00
3. the scan number (or row index) as a little-endian int64, then one 0x00
4. the peak count as a little-endian uint64
5. every m/z as a little-endian IEEE-754 float32
6. every intensity as a little-endian IEEE-754 float32
"""
from __future__ import annotations

import hashlib
import struct
from typing import Sequence

import numpy as np

HASH_LEN = 6


def content_hash(dataset: str, raw: str, ordinal: int, mz: Sequence[float], intensity: Sequence[float]) -> str:
    mz32 = np.ascontiguousarray(mz, dtype="<f4")
    in32 = np.ascontiguousarray(intensity, dtype="<f4")
    h = hashlib.sha256()
    h.update(dataset.encode("utf-8"))
    h.update(b"\x00")
    h.update(raw.encode("utf-8"))
    h.update(b"\x00")
    h.update(struct.pack("<q", int(ordinal)))
    h.update(b"\x00")
    h.update(struct.pack("<Q", mz32.size))
    h.update(mz32.tobytes())
    h.update(in32.tobytes())
    return h.hexdigest()[:HASH_LEN]


def spectrum_id(dataset: str, raw: str, mz: Sequence[float], intensity: Sequence[float],
                scan: int | None = None, row: int | None = None) -> str:
    """Id from the instrument scan number, or from the row index when there is none."""
    if scan is not None:
        marker, ordinal = "s", int(scan)
    elif row is not None:
        marker, ordinal = "r", int(row)
    else:
        raise ValueError("either scan or row is required")
    return f"{dataset}_{raw}_{marker}{ordinal}_{content_hash(dataset, raw, ordinal, mz, intensity)}"
