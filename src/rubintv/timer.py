"""Basic timing utility."""

from __future__ import annotations

import time
from typing import Any

__all__ = ["Timer"]


class Timer:
    """Time a context.

    Access the duration after the context exits with the ``seconds``
    attribute.
    """

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.seconds = time.perf_counter() - self._start
