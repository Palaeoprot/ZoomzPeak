"""
Portable path resolution for the ZoomzPeak store.

Ported from ``Reference-Data/MANIFESTS/paths.py`` (2026-08-29). Behaviour is unchanged:
the same constants resolve to the same locations, and the same environment variables
override them, so a script can switch its import from the old module to this one without
any change in where it reads or writes.

Nothing is hardcoded to one machine's username or drive layout -- paths resolve relative
to the user's home directory, so the same code works on Windows (``C:\\Users\\<user>\\...``)
and Linux (``/home/<user>/...``).

Layout assumed (sibling directories under ``Documents/GitHub``)::

    Documents/
        GitHub/
            ZoomzPeak/      -- this repo: builder code + specification
            MS1-Data/       -- ZooMS (MALDI-ToF) source data and legacy scripts
            MS2-Data/       -- LC-MS/MS source data and legacy scripts
            Reference-Data/ -- shared dictionaries, manifests
            _ZooMS/         -- ZooMS analysis pipeline (calibration, QC, modelling)
        parquet_master/     -- the store itself: data, not code, so NOT version
                               controlled and NOT inside any repo
            ZooMS_parquet/
            LC-MS_parquet/
            PSM_search_results/
            catalogs/

ZoomzPeak is a code + specification repository that *writes into* ``parquet_master``.
The data does not move and is never committed.

Drive-letter paths (``D:\\PRIDE``, ``H:\\My Drive``) are genuinely machine-specific --
there is no portable answer to "which secondary disk holds the raw downloads". Those are
read from environment variables with a Windows-typical default, so another machine can
override them without editing code.
"""

import os
from pathlib import Path

# --- Portable core (same shape on every machine) ---
HOME = Path.home()
DOCS_ROOT = HOME / "Documents"
GITHUB_ROOT = DOCS_ROOT / "GitHub"

ZOOMZPEAK = GITHUB_ROOT / "ZoomzPeak"
MS1_DATA = GITHUB_ROOT / "MS1-Data"
MS2_DATA = GITHUB_ROOT / "MS2-Data"
REFERENCE_DATA = GITHUB_ROOT / "Reference-Data"
ZOOMS_PIPELINE = GITHUB_ROOT / "_ZooMS"

# The controlled-vocabulary binding layer lives in this repo, beside the spec it binds.
VOCAB_DIR = ZOOMZPEAK / "vocab"
SPEC_DIR = ZOOMZPEAK / "spec"

PARQUET_MASTER = DOCS_ROOT / "parquet_master"
ZOOMS_PARQUET = PARQUET_MASTER / "ZooMS_parquet"
LCMS_PARQUET = PARQUET_MASTER / "LC-MS_parquet"
PSM_PARQUET = PARQUET_MASTER / "PSM_search_results"
CATALOGS = PARQUET_MASTER / "catalogs"

LCMS_MS2_DATASETS = LCMS_PARQUET / "parquet_datasets"
LCMS_MS1_ENVELOPE_DATASETS = LCMS_PARQUET / "ms1_envelope_datasets"
LCMS_EXPERIMENTS_METADATA = LCMS_PARQUET / "experiments_metadata"

ZOOMS_MS1_MALDI = ZOOMS_PARQUET / "zooms_ms1_maldi"
ZOOMS_PICKED = ZOOMS_PARQUET / "picked"
ZOOMS_EXPERIMENTS_METADATA = ZOOMS_PARQUET / "experiments_metadata"

# Catalog/bookkeeping files -- file-discovery manifest, deletion-safety audit, checksummed
# provenance, SDRF sidecars. These ARE organized parquet_master data (worth archiving),
# unlike .log files, which are ephemeral run output and stay in WORK_ROOT.
MASTER_MANIFEST = CATALOGS / "zooms_master_spectra_manifest.parquet"
RAW_DELETION_AUDIT = CATALOGS / "raw_deletion_audit.parquet"
VERIFICATION_REPORT = CATALOGS / "verification_report.parquet"
DRIVE_D_INVENTORY = CATALOGS / "drive_d_spectrum_inventory.parquet"
INSTRUMENT_HARVEST = CATALOGS / "instrument_metadata_harvest.parquet"
SDRF_DIR = CATALOGS / "sdrf"

# --- Machine-specific overrides (drive letters, mount points) ---


def _env_path(name: str, default: str) -> Path:
    """Environment override, treating an empty value as unset.

    ``os.environ.get(name, default)`` is wrong here: a variable set to the empty string
    -- which is what a blank line in a ``.env`` or an unset CI secret produces -- counts
    as "set", so the default never fires and ``Path("")`` silently resolves to the
    current working directory. For a root that scripts scan and delete beneath, that is
    a genuinely dangerous failure and it is silent. Fall back on blank as well as absent.
    """
    raw = os.environ.get(name)
    return Path(raw.strip() if raw and raw.strip() else default)


RAW_DOWNLOADS_ROOT = _env_path("PALAEOPROT_RAW_ROOT", r"D:\PRIDE")

# Working/scratch area for .log files only -- ephemeral run output, deliberately kept OUT
# of parquet_master (which gets copied to the archive).
WORK_ROOT = _env_path("PALAEOPROT_WORK_ROOT", r"C:\ZooMS_Master")

GDRIVE_ARCHIVE_ROOT = _env_path(
    "PALAEOPROT_GDRIVE_ARCHIVE",
    r"H:\My Drive\9 Agentic Environment\9. parquet_master",
)

__all__ = [
    "HOME", "DOCS_ROOT", "GITHUB_ROOT", "ZOOMZPEAK", "MS1_DATA", "MS2_DATA",
    "REFERENCE_DATA", "ZOOMS_PIPELINE", "VOCAB_DIR", "SPEC_DIR",
    "PARQUET_MASTER", "ZOOMS_PARQUET", "LCMS_PARQUET", "PSM_PARQUET", "CATALOGS",
    "LCMS_MS2_DATASETS", "LCMS_MS1_ENVELOPE_DATASETS", "LCMS_EXPERIMENTS_METADATA",
    "ZOOMS_MS1_MALDI", "ZOOMS_PICKED", "ZOOMS_EXPERIMENTS_METADATA",
    "MASTER_MANIFEST", "RAW_DELETION_AUDIT", "VERIFICATION_REPORT",
    "DRIVE_D_INVENTORY", "INSTRUMENT_HARVEST", "SDRF_DIR",
    "RAW_DOWNLOADS_ROOT", "WORK_ROOT", "GDRIVE_ARCHIVE_ROOT",
    "ensure_dirs",
]


def ensure_dirs() -> None:
    """Create the parquet_master category directories if they don't exist yet."""
    for d in (
        ZOOMS_PARQUET,
        ZOOMS_MS1_MALDI,
        ZOOMS_EXPERIMENTS_METADATA,
        LCMS_PARQUET,
        LCMS_MS2_DATASETS,
        LCMS_MS1_ENVELOPE_DATASETS,
        LCMS_EXPERIMENTS_METADATA,
        PSM_PARQUET,
        CATALOGS,
    ):
        d.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    for name in __all__:
        v = globals()[name]
        if not callable(v):
            print(f"{name} = {v}")
