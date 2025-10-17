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
    instrumentalness: Optional[float] = None
    key: Optional[int] = None               # numeric 0–11 if you choose to map
    liveness: Optional[float] = None
    loudness: Optional[float] = None        # LUFS in dB (negative)
    mode: Optional[int] = None              # 1=major, 0=minor
    speechiness: Optional[float] = None
    spotify_id: Optional[str] = None
    tempo: Optional[float] = None
    time_signature: Optional[int] = None
    type: str = "audio_features"
    valence: Optional[float] = None

    # Extra fields
    camelot: Optional[str] = None           #"8B", "10A", etc.
    key_name: Optional[str] = None          # "C", "F#", etc.
    mode_name: Optional[str] = None         # 'Major' or 'Minor'

    # Notes
    analysis_notes: Optional[List[str]] = None

    # allow passthrough if needed
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
