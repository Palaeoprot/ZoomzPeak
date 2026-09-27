"""
Tests for ZoomzPeak Portable Paths and Environment Variable Overrides.
"""

import os
from pathlib import Path
from zoomzpeak import paths


def test_core_paths():
    assert paths.DOCS_ROOT == Path.home() / "Documents"
    assert paths.GITHUB_ROOT == paths.DOCS_ROOT / "GitHub"
    assert paths.ZOOMZPEAK == paths.GITHUB_ROOT / "ZoomzPeak"
    assert paths.VOCAB_DIR == paths.ZOOMZPEAK / "vocab"
    assert paths.SPEC_DIR == paths.ZOOMZPEAK / "spec"
    assert paths.PARQUET_MASTER == paths.DOCS_ROOT / "parquet_master"
    assert paths.ZOOMS_PARQUET == paths.PARQUET_MASTER / "ZooMS_parquet"


def test_env_path_fallback():
    # Empty string should fall back to default
    default_val = r"C:\Default\Path"
    os.environ["__TEST_ENV_KEY"] = ""
    res = paths._env_path("__TEST_ENV_KEY", default_val)
    assert res == Path(default_val)

    # Whitespace should fall back to default
    os.environ["__TEST_ENV_KEY"] = "   "
    res = paths._env_path("__TEST_ENV_KEY", default_val)
    assert res == Path(default_val)

    # Valid value should be used
    custom_val = r"D:\Custom\Path"
    os.environ["__TEST_ENV_KEY"] = custom_val
    res = paths._env_path("__TEST_ENV_KEY", default_val)
    assert res == Path(custom_val)

    del os.environ["__TEST_ENV_KEY"]
