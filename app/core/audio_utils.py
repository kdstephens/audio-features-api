from __future__ import annotations

import io, os, tempfile
from typing import Dict, Any, Optional, List, Tuple

import numpy as np
import soundfile as sf
import librosa
import pyloudnorm as pyln
from fastapi import UploadFile, HTTPException

from app.core.config import TARGET_SR, CAMELOT_TABLE, KEY_TO_NUMBER
from app.core.models import AnalyzeQuery
from app.core import resolvers

# Krumhansl–Schmuckler tonal profiles
_KRUMHANSL_MAJOR = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88], dtype=float)
_KRUMHANSL_MINOR = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17], dtype=float)


def _guess_ext_from_magic(b: bytes) -> str:
    head = b[:16]
    if head.startswith(b"ID3") or head[:2] == b"\xff\xfb" or head[:2] == b"\xff\xf3" or head[:2] == b"\xff\xf2":
        return ".mp3"
    if b"ftyp" in head:
        # mp4/m4a family (AAC in MP4)
        return ".m4a"
    return ".mp3"  # safe default for Deezer; Apple tends to be m4a

def load_audio_from_bytes(b: bytes, target_sr: int = TARGET_SR) -> tuple[np.ndarray, int]:
    """
    Robust loader:
      1) try soundfile (WAV/OGG/FLAC/etc.)
      2) on failure, write bytes to a temp file with guessed extension
         so librosa can use audioread+ffmpeg to decode MP3/AAC (m4a)
    """
    bio = io.BytesIO(b)
    # 1) Try libsndfile via soundfile
    try:
        y, sr = sf.read(bio, dtype="float32", always_2d=False)
        if y.ndim > 1:
            y = np.mean(y, axis=1)
    except Exception:
        # 2) Fallback: use a temp file so librosa can trigger audioread/ffmpeg
        ext = _guess_ext_from_magic(b)
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        try:
            tmp.write(b)
            tmp.flush()
            tmp.close()
            y, sr = librosa.load(tmp.name, sr=None, mono=True)  # this path uses audioread if needed
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

    if sr != target_sr:
        y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
        sr = target_sr
    return y, sr


# --------- Feature extractors --------- #

def compute_duration_ms(y: np.ndarray, sr: int) -> int:
    return int(round(len(y) / sr * 1000.0))

def compute_tempo(y: np.ndarray, sr: int) -> float:
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return float(tempo)

def compute_loudness_lufs(y: np.ndarray, sr: int) -> float:
    meter = pyln.Meter(sr)  # ITU-R BS.1770
    return float(meter.integrated_loudness(y))

def compute_energy(y: np.ndarray) -> float:
    # Simple RMS→db→0..1 scaling (heuristic)
    rms = float(np.sqrt(np.mean(np.square(y))) + 1e-12)
    db = 20.0 * np.log10(rms)
    # scale -60..0 dB → 0..1
    return float(np.clip((db + 60.0) / 60.0, 0.0, 1.0))

def estimate_key_mode_krumhansl(y: np.ndarray, sr: int) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """
    Estimate (key_name, mode_name) using chroma (CQT) and Krumhansl-Schmuckler profiles.
    Returns e.g. ("C", "major") or (None, None) if inconclusive.
    """
    try:
        # Chroma via CQT is robust to timbre; you can try chroma_stft as a fallback.
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        pc = chroma.mean(axis=1)  # 12-vector
        if not np.any(pc):
            return None, None
        pc = pc / (pc.max() + 1e-9)

        def best_rotation(profile: np.ndarray) -> Tuple[int, float]:
            # correlate with all 12 rotations
            scores = [float(np.dot(pc, np.roll(profile, k))) for k in range(12)]
            k = int(np.argmax(scores))
            return k, scores[k]

        maj_k, maj_s = best_rotation(_KRUMHANSL_MAJOR)
        min_k, min_s = best_rotation(_KRUMHANSL_MINOR)

        if maj_s >= min_s:
            key_num, mode = maj_k, "major"
        else:
            key_num, mode = min_k, "minor"

        from app.core.config import NUMBER_TO_KEY_SHARP  # local import to avoid cycles
        key_name = NUMBER_TO_KEY_SHARP[key_num]
        return key_num, key_name, mode
    
    except Exception:
        return None, None, None

def to_camelot(key_name: Optional[str], mode_name: Optional[str]) -> Optional[str]:
    if not key_name or not mode_name:
        return None
    return CAMELOT_TABLE.get(f"{key_name} {mode_name}")

# Stub for ML classifiers (wire Essentia TF models later)
def classify_with_models(y: np.ndarray, sr: int) -> Dict[str, float]:
    # Return empty dict until models are plugged in
    return {}

# --------- Shaping --------- #

def to_spotify_like(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        # Spotify-like keys
        "acousticness": payload.get("acousticness"),
        "danceability": payload.get("danceability"),
        "duration_ms": payload.get("duration_ms"),
        "energy": payload.get("energy"),
        "instrumentalness": payload.get("instrumentalness"),
        "key": payload.get("key_number"),
        "liveness": payload.get("liveness"),
        "loudness": payload.get("loudness_db"),
        "mode": payload.get("mode_bit"),
        "speechiness": payload.get("speechiness"),
        "spotify_id": payload.get("spotify_id"),
        "tempo": payload.get("tempo"),
        "time_signature": payload.get("time_signature"),
        "type": "audio_features",
        "valence": payload.get("valence"),
        # Extras
        "key_name": payload.get("key_name"),
        "mode_name": payload.get("mode_name"),     # <-- add this
        "camelot": payload.get("camelot"),
        "analysis_notes": payload.get("analysis_notes", []),
    }

# --------- Orchestrators used by routes --------- #

async def analyze_audio_from_url(q: AnalyzeQuery) -> Dict[str, Any]:
    notes: List[str] = []
    spid = resolvers.parse_spotify_id(q.spotify) if q.spotify else None

    # Enrich metadata via Spotify (no audio downloading)
    if spid and q.spotify_bearer:
        try:
            spmeta = await resolvers.resolve_spotify_metadata(spid, q.spotify_bearer)
            if spmeta.get("title"):
                q.title = q.title or spmeta["title"]
            if spmeta.get("artist"):
                q.artist = q.artist or spmeta["artist"]
            if spmeta.get("preview_url"):
                notes.append("Spotify preview_url present; not used for downloads.")
        except Exception:
            notes.append("Spotify metadata fetch failed; continuing.")

    # Choose audio source
    if q.audio_url:
        audio_bytes = await resolvers.fetch_bytes(q.audio_url)
        notes.append("Used provided audio_url.")
    else:
        preview_meta = await resolvers.resolve_deezer_preview(q.artist, q.title)
        if not preview_meta:
            preview_meta = await resolvers.resolve_apple_preview(q.artist, q.title)
        if not preview_meta:
            raise HTTPException(status_code=404, detail="Could not resolve a preview from Deezer or Apple.")
        audio_bytes = await resolvers.fetch_bytes(preview_meta["preview_url"])
        notes.append(f"Fetched preview from {preview_meta['source']}.")

    # Decode & features
    y, sr = load_audio_from_bytes(audio_bytes, target_sr=TARGET_SR)
    duration_ms = compute_duration_ms(y, sr)
    tempo = round(compute_tempo(y, sr), 3)
    loudness_db = round(compute_loudness_lufs(y, sr), 3)
    energy = round(compute_energy(y), 3)

    # --- Key / Mode (Krumhansl–Schmuckler) ---
    key_number, key_name, mode_name = estimate_key_mode_krumhansl(y, sr)
    camelot = to_camelot(key_name, mode_name)

    ml = classify_with_models(y, sr)  # danceability/valence/etc. (currently empty)

    payload = {
        "spotify_id": spid or None,
        "duration_ms": duration_ms,
        "tempo": tempo,
        "loudness_db": loudness_db,
        "energy": energy,
        "key_name": key_name,
        "camelot": camelot,
        "key_number": key_number,                      
        "mode_bit": 1 if mode_name == "major" else (0 if mode_name == "minor" else None),
        'mode_name': mode_name,
        "time_signature": None,                   # low confidence from 30s; leave None
        "analysis_notes": notes,
        # classifiers (optional; None if not wired)
        "danceability": ml.get("danceability"),
        "valence": ml.get("valence") or ml.get("happiness"),
        "acousticness": ml.get("acousticness"),
        "instrumentalness": ml.get("instrumentalness"),
        "speechiness": ml.get("speechiness"),
        "liveness": ml.get("liveness"),
    }

    return to_spotify_like(payload)

async def analyze_audio_from_upload(file: UploadFile) -> Dict[str, Any]:
    b = await file.read()
    # Reuse core path by faking a query and bypassing network resolvers
    y, sr = load_audio_from_bytes(b, target_sr=TARGET_SR)
    duration_ms = compute_duration_ms(y, sr)
    tempo = round(compute_tempo(y, sr), 3)
    loudness_db = round(compute_loudness_lufs(y, sr), 3)
    energy = round(compute_energy(y), 3)

    # --- Key / Mode (Krumhansl–Schmuckler) ---
    key_number, key_name, mode_name = estimate_key_mode_krumhansl(y, sr)
    camelot = to_camelot(key_name, mode_name)

    ml = classify_with_models(y, sr)

    payload = {
        "id": None,
        "duration_ms": duration_ms,
        "tempo": tempo,
        "loudness_db": loudness_db,
        "energy": energy,
        "key_name": key_name,
        "camelot": camelot,
        "key_number": key_number,
        "mode_bit": 1 if mode_name == "major" else (0 if mode_name == "minor" else None),
        "mode_name": mode_name,
        "time_signature": None,
        "analysis_notes": ["Analyzed uploaded audio file."],
        "danceability": ml.get("danceability"),
        "valence": ml.get("valence") or ml.get("happiness"),
        "acousticness": ml.get("acousticness"),
        "instrumentalness": ml.get("instrumentalness"),
        "speechiness": ml.get("speechiness"),
        "liveness": ml.get("liveness"),
    }

    return to_spotify_like(payload)
