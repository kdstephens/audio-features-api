import io
import numpy as np
import soundfile as sf
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core import resolvers

client = TestClient(app)

def _sine_wave_wav_bytes(freq=440.0, sr=22050, duration_s=1.0, amplitude=0.2) -> bytes:
    """Generate a simple mono sine wave and return WAV bytes."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    y = amplitude * np.sin(2 * np.pi * freq * t).astype(np.float32)
    bio = io.BytesIO()
    sf.write(bio, y, sr, format="WAV")
    return bio.getvalue()


def test_analyze_upload_returns_fields():
    """Smoke test: /analyze/upload should parse audio and return Spotify-like fields."""
    wav_bytes = _sine_wave_wav_bytes(duration_s=1.0)
    files = {"file": ("tone.wav", wav_bytes, "audio/wav")}

    resp = client.post("/analyze/upload", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Core shape
    assert data["type"] == "audio_features"
    assert isinstance(data["tempo"], (int, float))  # may vary for a pure tone
    assert isinstance(data["energy"], (int, float))
    assert isinstance(data["loudness"], (int, float))
    assert isinstance(data["duration_ms"], int)
    assert "analysis_notes" in data and isinstance(data["analysis_notes"], list)

    # Sanity checks
    assert 900 <= data["duration_ms"] <= 1100  # ~1s tone
    assert data["loudness"] < 0  # LUFS should be negative


def test_analyze_with_mocked_resolvers(monkeypatch):
    """Hit /analyze with artist/title while mocking network to return local WAV bytes."""
    wav_bytes = _sine_wave_wav_bytes(duration_s=1.0)

    async def fake_resolve_deezer_preview(artist, title):
        return {
            "preview_url": "mock://wav",
            "title": title or "Mock Track",
            "artist": artist or "Mock Artist",
            "source": "deezer",
            "duration_full_s": 60,
        }

    async def fake_fetch_bytes(url: str) -> bytes:
        assert url == "mock://wav"
        return wav_bytes

    # Patch network-dependent functions
    monkeypatch.setattr(resolvers, "resolve_deezer_preview", fake_resolve_deezer_preview)
    monkeypatch.setattr(resolvers, "resolve_apple_preview", lambda a, t: None)  # not used
    monkeypatch.setattr(resolvers, "fetch_bytes", fake_fetch_bytes)

    payload = {"artist": "Aretha Franklin", "title": "Respect"}
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Core shape
    assert data["type"] == "audio_features"
    assert isinstance(data["tempo"], (int, float))
    assert isinstance(data["energy"], (int, float))
    assert isinstance(data["loudness"], (int, float))
    assert isinstance(data["duration_ms"], int)

    # Confirm mocked path was used
    assert any("deezer" in note.lower() for note in data.get("analysis_notes", []))
