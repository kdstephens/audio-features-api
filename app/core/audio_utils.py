import librosa, pyloudnorm, soundfile, numpy as np
from typing import Dict, Any

# IN PROGRESS: All DSP and feature extraction code. This file will handle
# - Loading audio (from bytes)
# - Computing tempo, loudness, energy
# - Optional Essentia model inference
# - Combining into a dict that looks like Spotify's JSON