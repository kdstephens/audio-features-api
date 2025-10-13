#!/usr/bin/env bash
# ========================================================
#  setup_env.sh — Create conda environment for audio-features-api
# ========================================================

set -e  # exit on first error
ENV_NAME="audio-features"
PYTHON_VERSION="3.10"

echo "🔧 Creating conda environment: $ENV_NAME (Python $PYTHON_VERSION)"

# Create environment if it doesn't exist
if conda info --envs | grep -q "$ENV_NAME"; then
    echo "✅ Conda environment '$ENV_NAME' already exists. Skipping creation."
else
    conda create -y -n "$ENV_NAME" python=$PYTHON_VERSION
fi

# Activate environment (non-interactive shells)
eval "$(conda shell.bash hook)"
conda activate "$ENV_NAME"

echo "📦 Installing system dependencies (ffmpeg, libsndfile)..."
conda install -y -c conda-forge ffmpeg libsndfile

echo "📦 Installing Python dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "⚠️ requirements.txt not found. Installing base dependencies manually."
    pip install fastapi uvicorn pydantic httpx librosa soundfile numpy scipy pyloudnorm mutagen
fi

echo "🧹 Cleaning up unused packages..."
conda clean -afy

echo "✅ Environment setup complete!"
echo ""
echo "Next steps:"
echo "  conda activate $ENV_NAME"
echo "  uvicorn app.main:app --reload --port 8080"