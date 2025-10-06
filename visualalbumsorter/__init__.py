"""Visual Album Sorter package."""

from importlib.metadata import PackageNotFoundError, version

try:  # pragma: no cover - metadata available in packaging contexts
    __version__ = version("visualalbumsorter")
except PackageNotFoundError:  # pragma: no cover - during local dev
    __version__ = "0.0.0"

__all__ = ["__version__"]
