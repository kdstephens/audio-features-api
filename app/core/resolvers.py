import io
import re
from typing import Optional, Dict, Any

import httpx

from app.core.config import (
    DEEZER_SEARCH_URL,
    ITUNES_SEARCH_URL,
    SPOTIFY_TRACK_URL,
    HTTP_TIMEOUT,
)

_SPOTIFY_ID_RE = re.compile(r"(?:spotify:track:|/track/)?([0-9A-Za-z]{22})")

def parse_spotify_id(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    m = _SPOTIFY_ID_RE.search(s)
    return m.group(1) if m else None

async def _fetch_json(url: str, params: dict | None = None, headers: dict | None = None):
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()

async def fetch_bytes(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content

# --------- External resolvers --------- #

async def resolve_deezer_preview(artist: Optional[str], title: Optional[str]) -> Optional[Dict[str, Any]]:
    if not (artist or title):
        return None
    q = " ".join(x for x in [artist, title] if x)
    data = await _fetch_json(DEEZER_SEARCH_URL, params={"q": q})
    for item in data.get("data", []):
        preview = item.get("preview")
        if preview:
            return {
                "preview_url": preview,           # mp3 30s
                "title": item.get("title"),
                "artist": item.get("artist", {}).get("name"),
                "source": "deezer",
                "duration_full_s": item.get("duration"),
            }
    return None

async def resolve_apple_preview(artist: Optional[str], title: Optional[str]) -> Optional[Dict[str, Any]]:
    if not (artist or title):
        return None
    term = " ".join(x for x in [artist, title] if x)
    data = await _fetch_json(ITUNES_SEARCH_URL, params={"term": term, "media": "music", "limit": 5})
    for item in data.get("results", []):
        preview = item.get("previewUrl")
        if preview:
            return {
                "preview_url": preview,           # AAC/MP4 30s
                "title": item.get("trackName"),
                "artist": item.get("artistName"),
                "source": "apple",
                "duration_full_s": (item.get("trackTimeMillis", 0) / 1000.0) if item.get("trackTimeMillis") else None,
            }
    return None

async def resolve_spotify_metadata(spotify_id: str, bearer_token: Optional[str]) -> Dict[str, Any]:
    if not bearer_token:
        return {}
    headers = {"Authorization": f"Bearer {bearer_token}"}
    url = SPOTIFY_TRACK_URL.format(id=spotify_id)
    data = await _fetch_json(url, headers=headers)
    return {
        "title": data.get("name"),
        "artist": ", ".join(a["name"] for a in data.get("artists", [])),
        "preview_url": data.get("preview_url"),  # often null; do not download from Spotify
    }
