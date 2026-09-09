"""ZoomzPeak -- a community standard for palaeoproteomics experiment metadata.

See ``spec/`` for the specification and ``PLAN.md`` for the design rationale.
"""

__version__ = "0.1.0.dev0"

from zoomzpeak import paths, schema  # noqa: F401

__all__ = ["paths", "schema", "__version__"]
