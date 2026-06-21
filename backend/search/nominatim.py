"""Geocoding via the OSM Nominatim public API."""
from typing import List, Optional, Tuple

import requests

from backend.config import USER_AGENT, REQUEST_TIMEOUT

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"


class NominatimClient:
    """
    Thin wrapper around the Nominatim search endpoint.

    Usage policy: https://operations.openstreetmap.org/policies/nominatim/
    - Identify yourself via User-Agent (enforced here via the shared USER_AGENT).
    - No bulk / automated requests; only fire on explicit user action.
    """

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "en,ja;q=0.9",
        })

    def search(
        self,
        query: str,
        limit: int = 5,
        country_codes: Optional[str] = "jp",
    ) -> List[dict]:
        """
        Return a list of Nominatim result dicts for *query*.

        Each dict has at least: lat, lon, display_name, type, importance.
        """
        if not query.strip():
            return []

        params: dict = {
            "q": query,
            "format": "jsonv2",
            "limit": limit,
            "addressdetails": 1,
        }
        if country_codes:
            params["countrycodes"] = country_codes

        try:
            resp = self._session.get(
                NOMINATIM_SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []

    def get_first(self, query: str) -> Optional[Tuple[float, float, str]]:
        """Return *(lat, lon, display_name)* for the top result, or None."""
        results = self.search(query)
        if not results:
            return None
        r = results[0]
        return float(r["lat"]), float(r["lon"]), r.get("display_name", "")
