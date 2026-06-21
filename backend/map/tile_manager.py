"""Tile fetching (with rate-limit awareness) and viewport compositing."""
import io
import math
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional, Dict, Tuple

import requests
from PIL import Image, ImageDraw, ImageFont

from backend.config import (
    OSM_TILE_URL,
    USER_AGENT,
    REQUEST_TIMEOUT,
    MAX_CONCURRENT_TILE_FETCHES,
    TILE_SIZE,
)
from backend.map.tile_cache import TileCache
from backend.map.geo_utils import lat_lon_to_tile_float, clamp_lat, clamp_lon, clamp_zoom


class TileManager:
    """Fetches, caches, and composites OSM raster tiles."""

    def __init__(self) -> None:
        self._cache = TileCache()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})
        self._pool = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TILE_FETCHES)
        self._placeholder: Optional[Image.Image] = None

    # ------------------------------------------------------------------
    # Tile fetching
    # ------------------------------------------------------------------

    def _placeholder_tile(self) -> Image.Image:
        if self._placeholder is None:
            img = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (210, 210, 210, 255))
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 0, TILE_SIZE - 1, TILE_SIZE - 1], outline=(180, 180, 180))
            self._placeholder = img
        return self._placeholder

    def fetch_tile(self, zoom: int, x: int, y: int) -> Optional[Image.Image]:
        """Return tile image, or None on error. Uses disk cache."""
        n = 2 ** zoom
        if not (0 <= x < n and 0 <= y < n):
            return None

        cached = self._cache.get(zoom, x, y)
        if cached is not None:
            return cached

        try:
            url = OSM_TILE_URL.format(z=zoom, x=x, y=y)
            resp = self._session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            tile = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            self._cache.put(zoom, x, y, tile)
            return tile
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Viewport rendering
    # ------------------------------------------------------------------

    def render_viewport(
        self,
        lat: float,
        lon: float,
        zoom: int,
        width_px: int,
        height_px: int,
    ) -> Image.Image:
        """
        Composite all tiles that cover the viewport into a single RGBA image.

        Tiles are fetched concurrently from the thread pool. Missing tiles
        (network error) are replaced with a placeholder so the result is
        always a complete image.
        """
        lat = clamp_lat(lat)
        lon = clamp_lon(lon)
        zoom = clamp_zoom(zoom)

        # Centre of viewport in fractional tile coordinates
        cx, cy = lat_lon_to_tile_float(lat, lon, zoom)

        # Top-left corner of the viewport in tile coords
        f_left = cx - width_px / (2.0 * TILE_SIZE)
        f_top = cy - height_px / (2.0 * TILE_SIZE)

        i_left = math.floor(f_left)
        i_top = math.floor(f_top)

        # Sub-tile pixel offset of the top-left tile inside the viewport
        ox = int((f_left - i_left) * TILE_SIZE)
        oy = int((f_top - i_top) * TILE_SIZE)

        tiles_x = math.ceil((width_px + ox) / TILE_SIZE) + 1
        tiles_y = math.ceil((height_px + oy) / TILE_SIZE) + 1

        # Submit fetches concurrently
        futures: Dict[Tuple[int, int], Future] = {}
        for dy in range(tiles_y):
            for dx in range(tiles_x):
                tx, ty = i_left + dx, i_top + dy
                futures[(tx, ty)] = self._pool.submit(self.fetch_tile, zoom, tx, ty)

        # Composite result image
        result = Image.new("RGBA", (width_px, height_px), (220, 220, 220, 255))

        for dy in range(tiles_y):
            for dx in range(tiles_x):
                tx, ty = i_left + dx, i_top + dy
                px = dx * TILE_SIZE - ox
                py = dy * TILE_SIZE - oy
                if px >= width_px or py >= height_px:
                    continue

                tile = futures[(tx, ty)].result()
                if tile is None:
                    tile = self._placeholder_tile()

                result.paste(tile, (px, py))

        return result

    def prefetch_around(self, lat: float, lon: float, zoom: int) -> None:
        """Warm the cache for tiles one step beyond the visible area."""
        cx, cy = lat_lon_to_tile_float(lat, lon, zoom)
        ix, iy = int(cx), int(cy)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                tx, ty = ix + dx, iy + dy
                if not self._cache.has(zoom, tx, ty):
                    self._pool.submit(self.fetch_tile, zoom, tx, ty)
