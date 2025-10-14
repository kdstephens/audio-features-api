from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict

class AnalyzeQuery(BaseModel):
    spotify: Optional[str] = None           # URL or 22-char ID
    artist: Optional[str] = None
    title: Optional[str] = None
    audio_url: Optional[str] = None         # direct URL to audio bytes (mp3/aac/etc.)
    spotify_bearer: Optional[str] = None    # for metadata only (no audio downloads)

class AudioFeaturesResponse(BaseModel):
    # Spotify-like fields
    acousticness: Optional[float] = None
    danceability: Optional[float] = None
    duration_ms: Optional[int] = None
    energy: Optional[float] = None
    id: Optional[str] = None
    instrumentalness: Optional[float] = None
    key: Optional[int] = None               # numeric 0–11 if you choose to map
    liveness: Optional[float] = None
    loudness: Optional[float] = None        # LUFS in dB (negative)
    mode: Optional[int] = None              # 1=major, 0=minor
    speechiness: Optional[float] = None
    tempo: Optional[float] = None
    time_signature: Optional[int] = None
    type: str = "audio_features"
    valence: Optional[float] = None

    # Helpful extras
    key_name: Optional[str] = None
    camelot: Optional[str] = None
    analysis_notes: Optional[List[str]] = None

    # allow passthrough if needed
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
