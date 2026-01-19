"""
FastAPI Backend for Beat-Reactive Video Generator
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from audio_analysis import analyze_audio, get_waveform_data, get_audio_duration, AudioFeatures
from effect_engine import EffectSettings, calculate_effect_parameters
from video_renderer import render_video, RenderSettings, AspectRatio
from playbook_generator import generate_playbook


# Create app
app = FastAPI(title="Beat-Reactive Video Generator", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage directories
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Mount static files for serving outputs
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# In-memory session storage (for simplicity)
sessions = {}


class SessionData(BaseModel):
    session_id: str
    image_path: Optional[str] = None
    audio_path: Optional[str] = None
    audio_duration: Optional[float] = None
    start_time: float = 0.0
    end_time: Optional[float] = None
    aspect_ratio: str = "9:16"
    motion_intensity: int = 50
    beat_reactivity: int = 50
    energy_level: int = 50
    output_path: Optional[str] = None
    render_status: str = "idle"  # idle, rendering, complete, error
    render_progress: float = 0.0
    playbook: Optional[dict] = None


class GenerateRequest(BaseModel):
    session_id: str
    start_time: float = 0.0
    end_time: Optional[float] = None
    aspect_ratio: str = "9:16"
    motion_intensity: int = 50
    beat_reactivity: int = 50
    energy_level: int = 50


class ExportRequest(BaseModel):
    session_id: str
    quality: str = "high"  # low, medium, high


@app.get("/")
async def root():
    return {"message": "Beat-Reactive Video Generator API", "version": "1.0.0"}


@app.post("/session/create")
async def create_session():
    """Create a new editing session."""
    session_id = str(uuid.uuid4())
    sessions[session_id] = SessionData(session_id=session_id)
    return {"session_id": session_id}


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session data."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]


@app.post("/upload/image/{session_id}")
async def upload_image(session_id: str, file: UploadFile = File(...)):
    """Upload cover art image."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type. Use JPEG, PNG, WebP, or GIF.")
    
    # Save file
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    
    ext = Path(file.filename).suffix or ".jpg"
    image_path = session_dir / f"cover{ext}"
    
    with open(image_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    sessions[session_id].image_path = str(image_path)
    
    return {"message": "Image uploaded", "path": str(image_path)}


@app.post("/upload/audio/{session_id}")
async def upload_audio(session_id: str, file: UploadFile = File(...)):
    """Upload audio file."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate file type
    allowed_types = ["audio/mpeg", "audio/wav", "audio/mp3", "audio/x-wav", "audio/flac", "audio/ogg"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid audio type. Use MP3, WAV, FLAC, or OGG.")
    
    # Save file
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    
    ext = Path(file.filename).suffix or ".mp3"
    audio_path = session_dir / f"audio{ext}"
    
    with open(audio_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Get audio duration
    duration = get_audio_duration(str(audio_path))
    
    sessions[session_id].audio_path = str(audio_path)
    sessions[session_id].audio_duration = duration
    sessions[session_id].end_time = min(30.0, duration)  # Default 30s or full duration
    
    return {
        "message": "Audio uploaded",
        "path": str(audio_path),
        "duration": duration
    }


@app.get("/audio/waveform/{session_id}")
async def get_waveform(session_id: str, num_points: int = 1000):
    """Get waveform data for visualization."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    if not session.audio_path:
        raise HTTPException(status_code=400, detail="No audio uploaded")
    
    waveform = get_waveform_data(session.audio_path, num_points)
    
    return {
        "waveform": waveform,
        "duration": session.audio_duration
    }


@app.get("/audio/stream/{session_id}")
async def stream_audio(session_id: str):
    """Stream the uploaded audio file for preview playback."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    if not session.audio_path:
        raise HTTPException(status_code=400, detail="No audio uploaded")
    
    audio_path = Path(session.audio_path)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Determine media type from extension
    ext = audio_path.suffix.lower()
    media_types = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
    }
    media_type = media_types.get(ext, "audio/mpeg")
    
    return FileResponse(audio_path, media_type=media_type)


@app.get("/audio/analysis/{session_id}")
async def get_audio_analysis(session_id: str):
    """Get full audio analysis for the selected region."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    if not session.audio_path:
        raise HTTPException(status_code=400, detail="No audio uploaded")
    
    start = session.start_time
    duration = (session.end_time or 30.0) - start
    
    features = analyze_audio(session.audio_path, start_time=start, duration=duration)
    
    return {
        "tempo": features.tempo,
        "duration": features.duration,
        "beat_count": len(features.beat_times),
        "beat_times": features.beat_times,
        "beat_strengths": features.beat_strengths
    }


def render_video_task(session_id: str, settings: GenerateRequest):
    """Background task to render video."""
    try:
        session = sessions[session_id]
        session.render_status = "rendering"
        session.render_progress = 0.0
        
        # Analyze audio
        start = settings.start_time
        duration = (settings.end_time or 30.0) - start
        
        features = analyze_audio(session.audio_path, start_time=start, duration=duration)
        
        # Calculate effect parameters
        effect_settings = EffectSettings(
            motion_intensity=settings.motion_intensity / 100.0,
            beat_reactivity=settings.beat_reactivity / 100.0,
            energy_level=settings.energy_level / 100.0
        )
        
        effect_params = calculate_effect_parameters(features, effect_settings)
        
        # Parse aspect ratio
        aspect_map = {
            "9:16": AspectRatio.VERTICAL,
            "1:1": AspectRatio.SQUARE,
            "16:9": AspectRatio.HORIZONTAL,
            "4:5": AspectRatio.PORTRAIT
        }
        aspect = aspect_map.get(settings.aspect_ratio, AspectRatio.VERTICAL)
        
        # Render video
        output_dir = OUTPUT_DIR / session_id
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "preview.mp4"
        
        render_settings = RenderSettings(
            aspect_ratio=aspect,
            fps=24,  # Lower FPS for faster preview
            quality="medium",
            duration=duration,
            preview=True  # Enable fast preview mode
        )
        
        def progress_callback(progress: float):
            session.render_progress = progress
        
        render_video(
            image_path=session.image_path,
            audio_path=session.audio_path,
            output_path=str(output_path),
            effect_params=effect_params,
            render_settings=render_settings,
            audio_start=start,
            progress_callback=progress_callback
        )
        
        # Generate playbook
        playbook = generate_playbook(effect_settings, features, effect_params)
        
        session.output_path = str(output_path)
        session.render_status = "complete"
        session.render_progress = 1.0
        session.playbook = playbook
        
    except Exception as e:
        session.render_status = "error"
        session.playbook = {"error": str(e)}
        print(f"Render error: {e}")


@app.post("/generate")
async def generate_video(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Start video generation."""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[request.session_id]
    
    if not session.image_path:
        raise HTTPException(status_code=400, detail="No image uploaded")
    if not session.audio_path:
        raise HTTPException(status_code=400, detail="No audio uploaded")
    
    # Update session settings
    session.start_time = request.start_time
    session.end_time = request.end_time
    session.aspect_ratio = request.aspect_ratio
    session.motion_intensity = request.motion_intensity
    session.beat_reactivity = request.beat_reactivity
    session.energy_level = request.energy_level
    
    # Start background render
    background_tasks.add_task(render_video_task, request.session_id, request)
    
    return {"message": "Generation started", "session_id": request.session_id}


@app.get("/generate/status/{session_id}")
async def get_generation_status(session_id: str):
    """Get video generation status."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    return {
        "status": session.render_status,
        "progress": session.render_progress,
        "output_path": session.output_path,
        "playbook": session.playbook
    }


@app.get("/preview/{session_id}")
async def get_preview(session_id: str):
    """Get the preview video URL."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if not session.output_path or session.render_status != "complete":
        raise HTTPException(status_code=400, detail="Video not ready")
    
    return {"video_url": f"/outputs/{session_id}/preview.mp4"}


def export_video_task(session_id: str, quality: str):
    """Background task to export video at full quality."""
    try:
        session = sessions[session_id]
        session.render_status = "exporting"
        session.render_progress = 0.0
        
        # Analyze audio
        start = session.start_time
        duration = (session.end_time or 30.0) - start
        
        features = analyze_audio(session.audio_path, start_time=start, duration=duration)
        
        # Calculate effect parameters
        effect_settings = EffectSettings(
            motion_intensity=session.motion_intensity / 100.0,
            beat_reactivity=session.beat_reactivity / 100.0,
            energy_level=session.energy_level / 100.0
        )
        
        effect_params = calculate_effect_parameters(features, effect_settings)
        
        # Parse aspect ratio
        aspect_map = {
            "9:16": AspectRatio.VERTICAL,
            "1:1": AspectRatio.SQUARE,
            "16:9": AspectRatio.HORIZONTAL,
            "4:5": AspectRatio.PORTRAIT
        }
        aspect = aspect_map.get(session.aspect_ratio, AspectRatio.VERTICAL)
        
        # Render at full quality
        output_dir = OUTPUT_DIR / session_id
        output_dir.mkdir(exist_ok=True)
        export_path = output_dir / "export.mp4"
        
        render_settings = RenderSettings(
            aspect_ratio=aspect,
            fps=30,  # Full FPS for export
            quality=quality,
            duration=duration,
            preview=False  # Full quality export
        )
        
        def progress_callback(progress: float):
            session.render_progress = progress
        
        render_video(
            image_path=session.image_path,
            audio_path=session.audio_path,
            output_path=str(export_path),
            effect_params=effect_params,
            render_settings=render_settings,
            audio_start=start,
            progress_callback=progress_callback
        )
        
        session.render_status = "export_complete"
        session.render_progress = 1.0
        
    except Exception as e:
        session.render_status = "error"
        print(f"Export error: {e}")


@app.post("/export")
async def export_video(request: ExportRequest, background_tasks: BackgroundTasks):
    """Export final high-quality video."""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[request.session_id]
    
    if not session.output_path:
        raise HTTPException(status_code=400, detail="No video to export. Generate first.")
    
    if not session.image_path or not session.audio_path:
        raise HTTPException(status_code=400, detail="Missing image or audio files.")
    
    # Start background export at full quality
    background_tasks.add_task(export_video_task, request.session_id, request.quality)
    
    return {
        "message": "Export started",
        "session_id": request.session_id
    }


@app.get("/download/{session_id}")
async def download_video(session_id: str):
    """Download the exported video."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    export_path = OUTPUT_DIR / session_id / "export.mp4"
    
    if not export_path.exists():
        raise HTTPException(status_code=404, detail="Export not found. Export first.")
    
    return FileResponse(
        export_path,
        media_type="video/mp4",
        filename="beat-reactive-video.mp4"
    )


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Clean up session data."""
    if session_id in sessions:
        # Remove files
        session_dir = UPLOAD_DIR / session_id
        output_dir = OUTPUT_DIR / session_id
        
        if session_dir.exists():
            shutil.rmtree(session_dir)
        if output_dir.exists():
            shutil.rmtree(output_dir)
        
        del sessions[session_id]
    
    return {"message": "Session deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

