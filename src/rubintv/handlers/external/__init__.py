"""Externally-accessible endpoint handlers that serve relative to
``/<app-name>/``.
"""

__all__ = [
    "get_index",
    "get_default_table",
    "get_table",
]
from rubintv.handlers.external.endpoints import get_default_table, get_table
from rubintv.handlers.external.index import get_index
