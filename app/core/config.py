# General configuration and constants for the service.

TARGET_SR = 22050

# External APIs
DEEZER_SEARCH_URL = "https://api.deezer.com/search"
ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
SPOTIFY_TRACK_URL = "https://api.spotify.com/v1/tracks/{id}"

# Networking
HTTP_TIMEOUT = 20  # seconds

# Key → Camelot mapping (Major=B, Minor=A)
CAMELOT_TABLE = {
    "C major": "8B",   "G major": "9B",   "D major": "10B",  "A major": "11B",
    "E major": "12B",  "B major": "1B",   "F# major": "2B",  "C# major": "3B",
    "F major": "7B",   "Bb major": "6B",  "Eb major": "5B",  "Ab major": "4B",
    "A minor": "8A",   "E minor": "9A",   "B minor": "10A",  "F# minor": "11A",
    "C# minor": "12A", "G# minor": "1A",  "D# minor": "2A",  "A# minor": "3A",
    "D minor": "7A",   "G minor": "6A",   "C minor": "5A",   "F minor": "4A",
}

# Note: numeric key mapping compatible with Spotify (C=0, C#/Db=1, ..., B=11)
KEY_TO_NUMBER = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
    "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11
}

# Prefer sharps to match common electronic music conventions (Camelot mapping above uses that).
NUMBER_TO_KEY_SHARP = {v: k for k, v in KEY_TO_NUMBER.items() if len(k) == 1 or "#" in k}

