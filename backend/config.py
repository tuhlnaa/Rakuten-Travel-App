"""Application-wide configuration."""
from pathlib import Path

APP_NAME = "Rakuten Travel Map"
APP_VERSION = "0.1.0"
CONTACT_EMAIL = "contact@rakuten-travel-map.example.com"

# OSM usage policy: identify your application with a descriptive User-Agent.
# See: https://operations.openstreetmap.org/policies/tiles/
USER_AGENT = f"{APP_NAME}/{APP_VERSION} (contact: {CONTACT_EMAIL})"

# Links required by OSM attribution policy
OSM_REPORT_URL = "https://www.openstreetmap.org/fixthemap"
OSM_COPYRIGHT_URL = "https://www.openstreetmap.org/copyright"

# OSM standard tile endpoint (z/x/y PNG)
OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
TILE_SIZE = 256
MIN_ZOOM = 1
MAX_ZOOM = 19

# Default view: central Tokyo
DEFAULT_LAT = 35.6762
DEFAULT_LON = 139.6503
DEFAULT_ZOOM = 12

# Initial window / map-area dimensions (pixels)
DEFAULT_VIEWPORT_WIDTH = 1024
DEFAULT_VIEWPORT_HEIGHT = 696  # 768 - 48 search bar - 24 attribution bar

# Network settings
REQUEST_TIMEOUT = 10          # seconds
MAX_CONCURRENT_TILE_FETCHES = 6

# Disk tile cache
CACHE_DIR: Path = Path.home() / ".cache" / "rakuten-travel" / "tiles"
CACHE_MAX_AGE_DAYS = 7
