"""Thread-safe disk cache for OSM tile PNGs."""
import time
import threading
from pathlib import Path
from typing import Optional

from PIL import Image

from backend.config import CACHE_DIR, CACHE_MAX_AGE_DAYS


class TileCache:
    def __init__(
        self,
        cache_dir: Path = CACHE_DIR,
        max_age_days: int = CACHE_MAX_AGE_DAYS,
    ) -> None:
        self._dir = cache_dir
        self._max_age = max_age_days * 86_400
        self._lock = threading.Lock()
        self._dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _path(self, zoom: int, x: int, y: int) -> Path:
        return self._dir / str(zoom) / str(x) / f"{y}.png"

    def _fresh(self, path: Path) -> bool:
        """Return True if the cached file exists and is still valid."""
        if not path.exists():
            return False
        return (time.time() - path.stat().st_mtime) < self._max_age

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, zoom: int, x: int, y: int) -> Optional[Image.Image]:
        path = self._path(zoom, x, y)
        with self._lock:
            if not self._fresh(path):
                return None
        try:
            return Image.open(path).convert("RGBA")
        except Exception:
            return None

    def put(self, zoom: int, x: int, y: int, tile: Image.Image) -> None:
        path = self._path(zoom, x, y)
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            tile.save(path, "PNG", optimize=False)

    def has(self, zoom: int, x: int, y: int) -> bool:
        with self._lock:
            return self._fresh(self._path(zoom, x, y))
