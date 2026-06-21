"""
Rakuten Travel Map – application entry point.

Wires the Slint frontend (frontend/ui/main.slint) to the Python backend
(tile management, geocoding) and drives the event loop.
"""
from __future__ import annotations

import math
import os
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path
from typing import Optional

# ── Third-party ──────────────────────────────────────────────────────────────
try:
    import slint
except ImportError:
    sys.exit("slint package not found – run: pip install slint")

try:
    from PIL import Image as PILImage
except ImportError:
    sys.exit("Pillow not found – run: pip install Pillow")

# ── Internal ─────────────────────────────────────────────────────────────────
from backend.config import (
    DEFAULT_LAT, DEFAULT_LON, DEFAULT_ZOOM,
    DEFAULT_VIEWPORT_WIDTH, DEFAULT_VIEWPORT_HEIGHT,
    MIN_ZOOM, MAX_ZOOM,
    OSM_REPORT_URL, OSM_COPYRIGHT_URL,
)
from backend.map.geo_utils import (
    lat_lon_to_tile_float,
    tile_float_to_lat_lon,
    clamp_lat, clamp_lon, clamp_zoom,
)
from backend.map.tile_manager import TileManager
from backend.search.nominatim import NominatimClient

# ── Slint UI file ─────────────────────────────────────────────────────────────
_UI_FILE = Path(__file__).parent / "frontend" / "ui" / "main.slint"


def _pil_to_slint(img: PILImage.Image) -> slint.Image:
    """
    Convert a PIL RGBA image to a slint.Image.

    Tries the in-memory RGBA8 API first (Slint ≥ 1.7); falls back to
    saving a temporary PNG on disk.
    """
    rgba = img.convert("RGBA")
    w, h = rgba.size
    raw = bytearray(rgba.tobytes())

    try:
        return slint.Image.create_from_rgba8(w, h, raw)
    except AttributeError:
        pass

    # Fallback: write to a fixed temp path and load from disk
    tmp = Path(tempfile.gettempdir()) / "rakuten_travel_map_tmp.png"
    rgba.save(tmp, "PNG")
    return slint.Image.load_from_path(str(tmp))


# ─────────────────────────────────────────────────────────────────────────────
class MapApp:
    """Bridges the Slint UI and the backend services."""

    def __init__(self) -> None:
        self._tiles = TileManager()
        self._geo = NominatimClient()

        # Current map state
        self.lat: float = DEFAULT_LAT
        self.lon: float = DEFAULT_LON
        self.zoom: int = DEFAULT_ZOOM
        self.vp_w: int = DEFAULT_VIEWPORT_WIDTH
        self.vp_h: int = DEFAULT_VIEWPORT_HEIGHT

        # Saved at the moment the user starts dragging
        self._pan_lat: float = DEFAULT_LAT
        self._pan_lon: float = DEFAULT_LON

        # Render sequencing – discard results that arrived out of order
        self._render_seq: int = 0

        # Load Slint module and create the window
        module = slint.load_file(str(_UI_FILE))
        self._win = module.MainWindow()
        self._win.zoom_level = self.zoom
        self._attach_callbacks()

        # Initial render
        self._render_async()

    # ── Callback wiring ───────────────────────────────────────────────────────

    def _attach_callbacks(self) -> None:
        w = self._win
        w.search_requested  = self._on_search
        w.map_pan_started   = self._on_pan_started
        w.map_pan           = self._on_pan
        w.map_zoom          = self._on_zoom
        w.map_resized       = self._on_resized
        w.report_issue      = lambda: webbrowser.open(OSM_REPORT_URL)
        w.open_copyright    = lambda: webbrowser.open(OSM_COPYRIGHT_URL)

    # ── Async render pipeline ─────────────────────────────────────────────────

    def _render_async(self) -> None:
        """Kick off a background render; update the UI when done."""
        self._render_seq += 1
        seq = self._render_seq

        lat, lon, zoom = self.lat, self.lon, self.zoom
        vp_w, vp_h = self.vp_w, self.vp_h

        def _worker() -> None:
            try:
                img = self._tiles.render_viewport(lat, lon, zoom, vp_w, vp_h)
                slint_img = _pil_to_slint(img)

                def _apply() -> None:
                    if self._render_seq == seq:
                        self._win.map_image = slint_img
                        self._win.zoom_level = zoom
                        self._win.loading = False

                try:
                    slint.invoke_from_event_loop(_apply)
                except AttributeError:
                    # Older Slint Python without invoke_from_event_loop
                    _apply()
            except Exception as exc:
                print(f"[render] {exc}", file=sys.stderr)

        self._win.loading = True
        threading.Thread(target=_worker, daemon=True).start()

        # Pre-warm nearby tiles in the background
        threading.Thread(
            target=self._tiles.prefetch_around,
            args=(lat, lon, zoom),
            daemon=True,
        ).start()

    # ── Slint callback handlers ───────────────────────────────────────────────

    def _on_search(self, query: str) -> None:
        if not query.strip():
            return
        self._win.searching = True
        self._win.status_text = f"Searching '{query}'…"

        def _worker() -> None:
            result = self._geo.get_first(query)

            def _apply() -> None:
                self._win.searching = False
                if result:
                    lat, lon, name = result
                    self.lat, self.lon, self.zoom = lat, lon, 14
                    short = name[:50] + ("…" if len(name) > 50 else "")
                    self._win.status_text = short
                    self._render_async()
                else:
                    self._win.status_text = "No results found"

            try:
                slint.invoke_from_event_loop(_apply)
            except AttributeError:
                _apply()

        threading.Thread(target=_worker, daemon=True).start()

    def _on_pan_started(self) -> None:
        self._pan_lat = self.lat
        self._pan_lon = self.lon

    def _on_pan(self, dx: float, dy: float) -> None:
        """Pan: dx/dy are total pixel offsets from the drag start."""
        n = 2.0 ** self.zoom
        start_cx, start_cy = lat_lon_to_tile_float(self._pan_lat, self._pan_lon, self.zoom)

        # Dragging right moves the map right → centre moves west (lower cx)
        new_cx = start_cx - dx / 256.0
        new_cy = start_cy - dy / 256.0

        new_lat, new_lon = tile_float_to_lat_lon(new_cx, new_cy, self.zoom)
        self.lat = clamp_lat(new_lat)
        self.lon = clamp_lon(new_lon)
        self._render_async()

    def _on_zoom(self, mouse_x: float, mouse_y: float, direction: int) -> None:
        """Zoom toward the cursor position."""
        old_zoom = self.zoom
        new_zoom = clamp_zoom(old_zoom + direction, MIN_ZOOM, MAX_ZOOM)
        if new_zoom == old_zoom:
            return

        # Pixel offset of cursor from viewport centre
        off_x = mouse_x - self.vp_w / 2.0
        off_y = mouse_y - self.vp_h / 2.0

        # Tile coords of the cursor in old zoom
        cx, cy = lat_lon_to_tile_float(self.lat, self.lon, old_zoom)
        cursor_tx = cx + off_x / 256.0
        cursor_ty = cy + off_y / 256.0
        cursor_lat, cursor_lon = tile_float_to_lat_lon(cursor_tx, cursor_ty, old_zoom)

        # At new zoom, keep cursor_lat/lon under mouse by adjusting centre
        new_cursor_tx, new_cursor_ty = lat_lon_to_tile_float(cursor_lat, cursor_lon, new_zoom)
        new_cx = new_cursor_tx - off_x / 256.0
        new_cy = new_cursor_ty - off_y / 256.0
        new_lat, new_lon = tile_float_to_lat_lon(new_cx, new_cy, new_zoom)

        self.lat = clamp_lat(new_lat)
        self.lon = clamp_lon(new_lon)
        self.zoom = new_zoom
        self._render_async()

    def _on_resized(self, width: float, height: float) -> None:
        new_w, new_h = max(1, int(width)), max(1, int(height))
        if (new_w, new_h) != (self.vp_w, self.vp_h):
            self.vp_w, self.vp_h = new_w, new_h
            self._render_async()

    # ── Public ───────────────────────────────────────────────────────────────

    def run(self) -> None:
        self._win.run()


# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    app = MapApp()
    app.run()


if __name__ == "__main__":
    main()
