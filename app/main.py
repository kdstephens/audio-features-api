from fastapi import FastAPI, UploadFile, File
from app.core.models import AnalyzeQuery
from app.core.audio_utils import analyze_audio_from_url, analyze_audio_from_upload

app = FastAPI(title="Audio Features API", version="0.1.0")

@app.post("/analyze")
async def analyze_track(q: AnalyzeQuery):
    return await analyze_audio_from_url(q)

@app.post("/analyze/upload")
async def analyze_track_upload(file: UploadFile = File(...)):
    return await analyze_audio_from_upload(file)