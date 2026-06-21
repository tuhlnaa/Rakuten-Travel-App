# Rakuten Travel – Japan Map Explorer

A desktop map application built with **Slint** (UI) and **Python** (backend).
Displays live [OpenStreetMap](https://www.openstreetmap.org/) tiles, supports
panning and zooming, and provides location search powered by Nominatim.

This project is the foundation for a Japan accommodation comparison app
(Rakuten Travel API integration – coming soon).

---

## Project structure

```
Rakuten-Travel-App/
├── main.py                        # Entry point – wires UI ↔ backend
├── pyproject.toml
├── requirements.txt
│
├── frontend/
│   └── ui/
│       ├── main.slint             # Root window component
│       └── components/
│           ├── map_view.slint     # Interactive tile viewport
│           ├── search_bar.slint   # Location search + branding
│           └── attribution.slint  # OSM copyright / report link
│
└── backend/
    ├── config.py                  # App-wide constants (User-Agent, cache dir…)
    ├── map/
    │   ├── geo_utils.py           # Web-Mercator tile math
    │   ├── tile_cache.py          # Thread-safe disk cache
    │   └── tile_manager.py        # Concurrent tile fetching + compositing
    └── search/
        └── nominatim.py           # OSM Nominatim geocoding client
```

---

## Requirements

| Tool | Version |
|------|---------|
| Python | ≥ 3.10 |
| Slint Python | ≥ 1.9 |
| Pillow | ≥ 10 |
| requests | ≥ 2.31 |

---

## Setup

```bash
# 1. Create and activate a virtual environment
conda create -n rakuten-travel python=3.12
conda activate rakuten-travel

# 2. Clone the repository
git clone https://github.com/tuhlnaa/Rakuten-Travel-App.git
cd Rakuten-Travel-App

# 3. Install dependencies (uv is optional but fast)
pip install uv
uv pip install -r requirements.txt

# 4. Run
python main.py
```

---

## Map interaction

| Action | Result |
|--------|--------|
| Left-drag | Pan the map |
| Scroll wheel | Zoom in / out (cursor-centred) |
| `+` / `−` buttons | Zoom in / out (map-centred) |
| Search box + Enter | Geocode and fly to location |

Default view: central Tokyo (zoom 12).

---

## OpenStreetMap compliance

This application follows the
[OSM Tile Usage Policy](https://operations.openstreetmap.org/policies/tiles/) and
the [Nominatim Usage Policy](https://operations.openstreetmap.org/policies/nominatim/):

- **User-Agent** — every HTTP request identifies the app and provides a contact
  address (`backend/config.py › USER_AGENT`).
- **Tile cache** — downloaded tiles are stored in `~/.cache/rakuten-travel/tiles/`
  for up to 7 days so the tile servers are not queried unnecessarily.
- **No bulk pre-fetching** — tiles are only fetched for the current viewport plus
  a small prefetch buffer of adjacent tiles.
- **Attribution** — an always-visible bar at the bottom of the window links to
  `openstreetmap.org/copyright`.
- **Report map issues** — the attribution bar contains a direct link to
  [openstreetmap.org/fixthemap](https://www.openstreetmap.org/fixthemap).
- **Contact email** — `contact@rakuten-travel-map.example.com`
  (update `CONTACT_EMAIL` in `backend/config.py` before deploying).

---

## Tile cache location

```
~/.cache/rakuten-travel/tiles/<zoom>/<x>/<y>.png
```

Tiles older than 7 days are re-fetched automatically.
To clear the cache manually:

```bash
rm -rf ~/.cache/rakuten-travel/tiles/
```

---

## Extending the app

| Feature | Where to start |
|---------|---------------|
| Accommodation search | `backend/` – add a `rakuten/` package |
| Map markers / pins | `frontend/ui/components/map_view.slint` – overlay `Rectangle` elements |
| Route display | `backend/map/tile_manager.py` – draw on the composited PIL image |
| Rust performance module | Add a `Cargo.toml` at the repo root and call via `PyO3` |

---

## License

See [LICENSE](LICENSE).

Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
available under the [Open Database Licence](https://opendatacommons.org/licenses/odbl/).
