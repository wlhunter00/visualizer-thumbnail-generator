"""
FastAPI Backend for Beat-Reactive Video Generator
Supports 13 customizable effects with AI-powered image analysis and auto-suggestions.
"""
from __future__ import annotations

import os
import uuid
import shutil
import time
import asyncio
import threading
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from audio_analysis import analyze_audio, get_waveform_data, get_audio_duration, AudioFeatures
from effect_engine import (
    EffectToggles, EffectToggle, ImageContext, SubjectBounds, GlowPoint,
    calculate_effect_parameters, toggles_from_dict, image_context_from_dict,
    legacy_settings_to_toggles
)
from video_renderer import render_video, RenderSettings, AspectRatio

# Load environment variables
load_dotenv()

# Create app
app = FastAPI(title="Beat-Reactive Video Generator", version="2.0.0")

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
DEMOS_DIR = Path("demos")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
DEMOS_DIR.mkdir(exist_ok=True)

# Mount static files for serving outputs
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# Mount demos directory (if it exists with content)
if DEMOS_DIR.exists() and any(DEMOS_DIR.iterdir()):
    app.mount("/demos", StaticFiles(directory="demos"), name="demos")

# In-memory session storage with lock for thread safety
sessions: Dict[str, SessionData] = {}
session_lock = threading.Lock()

# Session expiration settings - extended to 24 hours so sessions don't expire mid-work
SESSION_EXPIRY_SECONDS = 3600 * 24  # 24 hours
SESSION_CLEANUP_INTERVAL = 600  # Check every 10 minutes


def cleanup_expired_sessions():
    """Remove sessions that haven't been accessed in SESSION_EXPIRY_SECONDS."""
    current_time = time.time()
    expired_sessions = []
    
    with session_lock:
        for session_id, session in sessions.items():
            if current_time - session.last_accessed > SESSION_EXPIRY_SECONDS:
                expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        # Clean up files
        session_dir = UPLOAD_DIR / session_id
        output_dir = OUTPUT_DIR / session_id
        
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)
        if output_dir.exists():
            shutil.rmtree(output_dir, ignore_errors=True)
        
        with session_lock:
            if session_id in sessions:
                del sessions[session_id]
    
    if expired_sessions:
        print(f"Cleaned up {len(expired_sessions)} expired sessions")


async def session_cleanup_task():
    """Background task that periodically cleans up expired sessions."""
    while True:
        await asyncio.sleep(SESSION_CLEANUP_INTERVAL)
        cleanup_expired_sessions()


@app.on_event("startup")
async def startup_event():
    """Start background cleanup task on app startup."""
    # Note: We no longer delete files on startup - this preserves uploads if server restarts
    # Old sessions will be cleaned up when they expire (after 24 hours of inactivity)
    asyncio.create_task(session_cleanup_task())


# ============================================================================
# Pydantic Models
# ============================================================================

class SessionData(BaseModel):
    session_id: str
    image_path: Optional[str] = None
    audio_path: Optional[str] = None
    audio_duration: Optional[float] = None
    start_time: float = 0.0
    end_time: Optional[float] = None
    aspect_ratio: str = "9:16"
    
    # New: Image analysis results
    image_analysis: Optional[Dict[str, Any]] = None
    
    # New: Effect toggles (replaces old sliders)
    effect_toggles: Optional[Dict[str, Any]] = None
    
    # Resolution scale (1.0 = 1080p, 0.67 = 720p, etc.)
    resolution_scale: float = 1.0
    
    # Legacy support (to be deprecated)
    motion_intensity: int = 50
    beat_reactivity: int = 50
    energy_level: int = 50
    
    output_path: Optional[str] = None
    render_status: str = "idle"
    
    # Session tracking for cleanup
    created_at: float = 0.0
    last_accessed: float = 0.0
    render_progress: float = 0.0
    playbook: Optional[dict] = None
    
    # New: Custom particle sprite path
    particle_sprite_path: Optional[str] = None
    
    # Image transformation
    original_image_path: Optional[str] = None  # Original before transformation
    transformed_image_path: Optional[str] = None  # After transformation
    transform_status: str = "idle"  # idle, transforming, complete, error
    transform_preset: Optional[str] = None  # Which preset was used

    # Cached audio analysis for live preview (keyed by start/end region)
    audio_analysis_cache: Optional[Dict[str, Any]] = None
    audio_analysis_cache_key: Optional[str] = None


class EffectToggleModel(BaseModel):
    enabled: bool = False
    intensity: float = 0.5
    trigger_source: str = "beats"


class EffectTogglesRequest(BaseModel):
    element_glow: Optional[EffectToggleModel] = None
    element_scale: Optional[EffectToggleModel] = None
    neon_outline: Optional[EffectToggleModel] = None
    echo_trail: Optional[EffectToggleModel] = None
    particle_burst: Optional[EffectToggleModel] = None
    energy_trails: Optional[EffectToggleModel] = None
    light_flares: Optional[EffectToggleModel] = None
    glitch: Optional[EffectToggleModel] = None
    ripple_wave: Optional[EffectToggleModel] = None
    film_grain: Optional[EffectToggleModel] = None
    strobe_flash: Optional[EffectToggleModel] = None
    vignette_pulse: Optional[EffectToggleModel] = None
    background_dim: Optional[EffectToggleModel] = None


class GenerateRequest(BaseModel):
    session_id: str
    start_time: float = 0.0
    end_time: Optional[float] = None
    aspect_ratio: str = "9:16"
    
    # New: Effect toggles (preferred)
    effect_toggles: Optional[Dict[str, Any]] = None
    
    # Resolution scale (1.0 = 1080p base, 0.67 = 720p, 1.33 = 1440p, 2.0 = 4K)
    resolution_scale: Optional[float] = None
    
    # Legacy support
    motion_intensity: Optional[int] = None
    beat_reactivity: Optional[int] = None
    energy_level: Optional[int] = None


class SessionSettingsRequest(BaseModel):
    start_time: float = 0.0
    end_time: Optional[float] = None
    aspect_ratio: str = "9:16"
    effect_toggles: Optional[Dict[str, Any]] = None


class ExportRequest(BaseModel):
    session_id: str
    quality: str = "high"
    resolution_scale: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    aspect_ratio: Optional[str] = None
    effect_toggles: Optional[Dict[str, Any]] = None


class AutoSuggestRequest(BaseModel):
    session_id: str


class TransformImageRequest(BaseModel):
    preset_key: str  # Key of the preset to use (e.g., "huntingszn_teal")
    custom_prompt: Optional[str] = None  # Optional custom prompt (for "custom" preset)


# ============================================================================
# Basic Endpoints
# ============================================================================

@app.get("/")
async def root():
    return {
        "message": "Beat-Reactive Video Generator API",
        "version": "2.0.0",
        "features": ["13 customizable effects", "AI image analysis", "Auto-suggest settings"]
    }


@app.get("/demos/manifest")
async def get_demos_manifest():
    """Get the demos manifest with effect metadata."""
    manifest_path = DEMOS_DIR / "manifest.json"
    
    if not manifest_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Demo videos not generated yet. Run 'python generate_demos.py' in the backend folder."
        )
    
    import json
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    
    return manifest


@app.post("/session/create")
async def create_session():
    """Create a new editing session."""
    session_id = str(uuid.uuid4())
    current_time = time.time()
    with session_lock:
        sessions[session_id] = SessionData(
            session_id=session_id,
            created_at=current_time,
            last_accessed=current_time
        )
    return {"session_id": session_id}


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session data."""
    with session_lock:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        sessions[session_id].last_accessed = time.time()
        return sessions[session_id]


# ============================================================================
# Upload Endpoints
# ============================================================================

@app.post("/upload/image/{session_id}")
async def upload_image(session_id: str, file: UploadFile = File(...)):
    """Upload cover art image."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type. Use JPEG, PNG, WebP, or GIF.")
    
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    
    # Normalize extension
    ext = Path(file.filename).suffix.lower() or ".jpg"
    if ext == ".jpeg":
        ext = ".jpg"
    image_path = session_dir / f"cover{ext}"
    
    with open(image_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    sessions[session_id].image_path = str(image_path)
    # Reset analysis when new image uploaded
    sessions[session_id].image_analysis = None
    
    return {"message": "Image uploaded", "path": str(image_path)}


@app.post("/upload/audio/{session_id}")
async def upload_audio(session_id: str, file: UploadFile = File(...)):
    """Upload audio file."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    allowed_types = ["audio/mpeg", "audio/wav", "audio/mp3", "audio/x-wav", "audio/flac", "audio/ogg"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid audio type. Use MP3, WAV, FLAC, or OGG.")
    
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    
    ext = Path(file.filename).suffix or ".mp3"
    audio_path = session_dir / f"audio{ext}"
    
    with open(audio_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    duration = get_audio_duration(str(audio_path))
    
    sessions[session_id].audio_path = str(audio_path)
    sessions[session_id].audio_duration = duration
    sessions[session_id].end_time = min(30.0, duration)
    
    return {
        "message": "Audio uploaded",
        "path": str(audio_path),
        "duration": duration
    }


# ============================================================================
# Audio Endpoints
# ============================================================================

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
async def stream_audio(session_id: str, request: Request):
    """Stream the uploaded audio file for preview playback with Range request support."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    if not session.audio_path:
        raise HTTPException(status_code=400, detail="No audio uploaded")
    
    audio_path = Path(session.audio_path)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    ext = audio_path.suffix.lower()
    media_types = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
    }
    media_type = media_types.get(ext, "audio/mpeg")
    
    file_size = audio_path.stat().st_size
    
    # Handle Range requests for seeking support
    range_header = request.headers.get("range")
    
    if range_header:
        # Parse range header (e.g., "bytes=0-1023")
        try:
            range_spec = range_header.replace("bytes=", "")
            range_parts = range_spec.split("-")
            start = int(range_parts[0]) if range_parts[0] else 0
            end = int(range_parts[1]) if range_parts[1] else file_size - 1
        except (ValueError, IndexError):
            start = 0
            end = file_size - 1
        
        # Clamp values
        start = max(0, min(start, file_size - 1))
        end = max(start, min(end, file_size - 1))
        content_length = end - start + 1
        
        def iterfile():
            with open(audio_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                chunk_size = 64 * 1024  # 64KB chunks
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        
        return StreamingResponse(
            iterfile(),
            status_code=206,
            media_type=media_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
            }
        )
    
    # No range requested, return full file
    return FileResponse(
        audio_path, 
        media_type=media_type,
        headers={"Accept-Ranges": "bytes"}
    )


def _envelope_to_list(envelope: list) -> list:
    """Convert (time, value) tuples to JSON-serializable lists."""
    return [[float(t), float(v)] for t, v in envelope]


def audio_features_to_dict(features: AudioFeatures) -> Dict[str, Any]:
    """Serialize AudioFeatures for the live preview API."""
    return {
        "tempo": float(features.tempo),
        "duration": features.duration,
        "beat_count": len(features.beat_times),
        "beat_times": features.beat_times,
        "beat_strengths": features.beat_strengths,
        "onset_times": features.onset_times,
        "onset_strengths": features.onset_strengths,
        "energy_envelope": _envelope_to_list(features.energy_envelope),
        "low_freq_energy": _envelope_to_list(features.low_freq_energy),
        "mid_freq_energy": _envelope_to_list(features.mid_freq_energy),
        "high_freq_energy": _envelope_to_list(features.high_freq_energy),
        "onset_density": features.onset_density,
        "average_bass": features.average_bass,
        "average_mid": features.average_mid,
        "average_high": features.average_high,
        "dynamic_range": features.dynamic_range,
        "beat_strength_variance": features.beat_strength_variance,
        "average_energy": features.average_energy,
    }


def _apply_session_settings(session: SessionData, settings: SessionSettingsRequest) -> bool:
    """Apply settings to session. Returns True if region changed (cache invalid)."""
    region_changed = (
        session.start_time != settings.start_time
        or session.end_time != settings.end_time
    )
    session.start_time = settings.start_time
    session.end_time = settings.end_time
    session.aspect_ratio = settings.aspect_ratio
    if settings.effect_toggles is not None:
        session.effect_toggles = settings.effect_toggles
    if region_changed:
        session.audio_analysis_cache = None
        session.audio_analysis_cache_key = None
    session.last_accessed = time.time()
    return region_changed


@app.post("/session/settings/{session_id}")
async def sync_session_settings(session_id: str, settings: SessionSettingsRequest):
    """Sync frontend settings (region, aspect ratio, toggles) to session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    with session_lock:
        session = sessions[session_id]
        region_changed = _apply_session_settings(session, settings)

    return {
        "message": "Settings synced",
        "region_changed": region_changed,
    }


@app.get("/audio/analysis/{session_id}")
async def get_audio_analysis(session_id: str):
    """Get full audio analysis for the selected region."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    with session_lock:
        session = sessions[session_id]
        if not session.audio_path:
            raise HTTPException(status_code=400, detail="No audio uploaded")

        start = session.start_time
        end = session.end_time or 30.0
        cache_key = f"{start}:{end}"

        if (
            session.audio_analysis_cache is not None
            and session.audio_analysis_cache_key == cache_key
        ):
            session.last_accessed = time.time()
            return session.audio_analysis_cache

        audio_path = session.audio_path

    duration = end - start
    features = analyze_audio(audio_path, start_time=start, duration=duration)
    result = audio_features_to_dict(features)

    with session_lock:
        if session_id in sessions:
            sessions[session_id].audio_analysis_cache = result
            sessions[session_id].audio_analysis_cache_key = cache_key
            sessions[session_id].last_accessed = time.time()

    return result


# ============================================================================
# NEW: Image Analysis Endpoints
# ============================================================================

@app.post("/analyze-image/{session_id}")
async def analyze_image_endpoint(session_id: str):
    """
    Analyze the uploaded image using AI to detect subject, colors, and glow points.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    if not session.image_path:
        raise HTTPException(status_code=400, detail="No image uploaded")
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500, 
            detail="OPENAI_API_KEY not configured. Set it in backend/.env file."
        )
    
    try:
        from image_analysis import analyze_image, image_analysis_to_dict
        
        analysis = await analyze_image(session.image_path)
        analysis_dict = image_analysis_to_dict(analysis)
        
        # Store in session
        sessions[session_id].image_analysis = analysis_dict
        
        return {
            "message": "Image analyzed successfully",
            "analysis": analysis_dict
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")


@app.post("/generate-particles/{session_id}")
async def generate_particles_endpoint(session_id: str):
    """
    Generate custom particle sprites based on image analysis.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500, 
            detail="OPENAI_API_KEY not configured"
        )
    
    # Get colors and style from analysis, or use defaults
    analysis = session.image_analysis or {}
    colors = analysis.get("colors", ["#FFFFFF", "#FFD700"])
    style = analysis.get("suggested_particle_style", "glowing sparkles")
    
    try:
        from image_analysis import generate_particle_sprite
        
        session_dir = UPLOAD_DIR / session_id
        session_dir.mkdir(exist_ok=True)
        output_path = str(session_dir / "particle_sprite.png")
        
        await generate_particle_sprite(colors, style, output_path)
        
        sessions[session_id].particle_sprite_path = output_path
        
        return {
            "message": "Particle sprite generated",
            "path": output_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Particle generation failed: {str(e)}")


@app.post("/auto-suggest/{session_id}")
async def auto_suggest_endpoint(session_id: str):
    """
    Get AI-suggested effect settings based on image and audio analysis.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if not session.image_path:
        raise HTTPException(status_code=400, detail="No image uploaded")
    if not session.audio_path:
        raise HTTPException(status_code=400, detail="No audio uploaded")
    
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500, 
            detail="OPENAI_API_KEY not configured"
        )
    
    try:
        # Analyze image if not already done
        if not session.image_analysis:
            from image_analysis import analyze_image, image_analysis_to_dict
            analysis = await analyze_image(session.image_path)
            session.image_analysis = image_analysis_to_dict(analysis)
        
        # Get audio metrics
        start = session.start_time
        duration = (session.end_time or 30.0) - start
        features = analyze_audio(session.audio_path, start_time=start, duration=duration)
        
        audio_metrics = {
            "tempo": features.tempo,
            "onset_density": features.onset_density,
            "average_bass": features.average_bass,
            "average_mid": features.average_mid,
            "average_high": features.average_high,
            "dynamic_range": features.dynamic_range,
            "beat_strength_variance": features.beat_strength_variance,
            "average_energy": features.average_energy
        }
        
        # Get AI suggestions
        from image_analysis import (
            auto_suggest_effects, effect_suggestion_to_dict,
            ImageAnalysis, SubjectBounds as IASubjectBounds, GlowPoint as IAGlowPoint
        )
        
        # Reconstruct ImageAnalysis from dict
        analysis_dict = session.image_analysis
        image_analysis = ImageAnalysis(
            subject=analysis_dict.get("subject", "subject"),
            subject_description=analysis_dict.get("subject_description", ""),
            bounds=IASubjectBounds(
                x=analysis_dict.get("bounds", {}).get("x", 0.25),
                y=analysis_dict.get("bounds", {}).get("y", 0.25),
                w=analysis_dict.get("bounds", {}).get("w", 0.5),
                h=analysis_dict.get("bounds", {}).get("h", 0.5)
            ),
            glow_points=[
                IAGlowPoint(x=gp["x"], y=gp["y"], intensity=gp.get("intensity", 1.0))
                for gp in analysis_dict.get("glow_points", [])
            ],
            colors=analysis_dict.get("colors", []),
            mood=analysis_dict.get("mood", "neutral"),
            suggested_particle_style=analysis_dict.get("suggested_particle_style", "sparkles")
        )
        
        suggestion = await auto_suggest_effects(image_analysis, audio_metrics)
        suggestion_dict = effect_suggestion_to_dict(suggestion)
        
        # Store in session
        sessions[session_id].effect_toggles = suggestion_dict
        
        return {
            "message": "Settings suggested",
            "effect_toggles": suggestion_dict,
            "audio_metrics": audio_metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-suggest failed: {str(e)}")


@app.post("/effect-toggles/{session_id}")
async def update_effect_toggles(session_id: str, toggles: Dict[str, Any]):
    """Update effect toggles for a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    sessions[session_id].effect_toggles = toggles
    return {"message": "Effect toggles updated"}


# ============================================================================
# Image Transformation Endpoints
# ============================================================================

@app.get("/transform/presets")
async def get_transform_presets():
    """Get all available transformation presets."""
    from transform_presets import get_all_presets
    return {"presets": get_all_presets()}


def transform_image_task(session_id: str, preset_key: str, custom_prompt: Optional[str] = None):
    """Background task to transform an image."""
    try:
        # Get session data with lock
        with session_lock:
            if session_id not in sessions:
                print(f"Session {session_id} not found, aborting transform")
                return
            session = sessions[session_id]
            session.transform_status = "transforming"
            image_path = session.image_path
        
        if not image_path:
            with session_lock:
                if session_id in sessions:
                    sessions[session_id].transform_status = "error"
            return
        
        # Get the preset prompt
        from transform_presets import get_preset, PRESETS
        
        if preset_key == "custom" and custom_prompt:
            prompt = custom_prompt
        elif preset_key in PRESETS:
            preset = get_preset(preset_key)
            prompt = preset.prompt
        else:
            with session_lock:
                if session_id in sessions:
                    sessions[session_id].transform_status = "error"
            return
        
        # Run the transformation synchronously (we're in a background thread)
        import asyncio
        from image_analysis import transform_image
        
        session_dir = UPLOAD_DIR / session_id
        output_path = str(session_dir / "transformed_cover.png")
        
        # Run async function in new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(transform_image(image_path, prompt, output_path))
        finally:
            loop.close()
        
        # Update session with results
        with session_lock:
            if session_id in sessions:
                sessions[session_id].original_image_path = image_path
                sessions[session_id].transformed_image_path = output_path
                sessions[session_id].transform_status = "complete"
                sessions[session_id].transform_preset = preset_key
                # Also set as the current image for video generation
                sessions[session_id].image_path = output_path
        
    except Exception as e:
        with session_lock:
            if session_id in sessions:
                sessions[session_id].transform_status = "error"
        print(f"Transform error: {e}")
        import traceback
        traceback.print_exc()


@app.post("/transform-image/{session_id}")
async def transform_image_endpoint(
    session_id: str, 
    request: TransformImageRequest,
    background_tasks: BackgroundTasks
):
    """
    Transform an uploaded image using a preset style.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    if not session.image_path:
        raise HTTPException(status_code=400, detail="No image uploaded")
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500, 
            detail="OPENAI_API_KEY not configured. Set it in backend/.env file."
        )
    
    # Validate preset
    from transform_presets import PRESETS
    if request.preset_key != "custom" and request.preset_key not in PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown preset: {request.preset_key}")
    
    if request.preset_key == "custom" and not request.custom_prompt:
        raise HTTPException(status_code=400, detail="Custom preset requires a prompt")
    
    # Start background transformation
    background_tasks.add_task(
        transform_image_task, 
        session_id, 
        request.preset_key,
        request.custom_prompt
    )
    
    return {
        "message": "Transformation started",
        "session_id": session_id,
        "preset": request.preset_key
    }


@app.get("/transform/status/{session_id}")
async def get_transform_status(session_id: str):
    """Get the status of an image transformation."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    return {
        "status": session.transform_status,
        "preset": session.transform_preset,
        "original_image": session.original_image_path,
        "transformed_image": session.transformed_image_path,
    }


@app.get("/transform/result/{session_id}")
async def get_transform_result(session_id: str):
    """Get the transformed image."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if session.transform_status != "complete":
        raise HTTPException(status_code=400, detail="Transformation not complete")
    
    if not session.transformed_image_path:
        raise HTTPException(status_code=404, detail="Transformed image not found")
    
    transformed_path = Path(session.transformed_image_path)
    if not transformed_path.exists():
        raise HTTPException(status_code=404, detail="Transformed image file not found")
    
    return FileResponse(
        transformed_path,
        media_type="image/png",
        filename="transformed_cover.png"
    )


@app.get("/image/{session_id}/{image_type}")
async def get_session_image(session_id: str, image_type: str):
    """Get an image from the session (original or transformed)."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if image_type == "original":
        image_path = session.original_image_path or session.image_path
    elif image_type == "transformed":
        image_path = session.transformed_image_path
    elif image_type == "current":
        image_path = session.image_path
    else:
        raise HTTPException(status_code=400, detail="Invalid image type. Use: original, transformed, current")
    
    if not image_path:
        raise HTTPException(status_code=404, detail=f"No {image_type} image available")
    
    path = Path(image_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    
    # Determine media type
    ext = path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_types.get(ext, "image/jpeg")
    
    return FileResponse(path, media_type=media_type)


# ============================================================================
# Generation Endpoints
# ============================================================================

def render_video_task(session_id: str, settings: GenerateRequest):
    """Background task to render video."""
    try:
        # Get session data with lock
        with session_lock:
            if session_id not in sessions:
                print(f"Session {session_id} not found, aborting render")
                return
            session = sessions[session_id]
            session.render_status = "rendering"
            session.render_progress = 0.0
            # Copy needed data while holding lock
            audio_path = session.audio_path
            image_path = session.image_path
            session_effect_toggles = session.effect_toggles
            session_image_analysis = session.image_analysis
            particle_sprite_path = session.particle_sprite_path
        
        # Analyze audio (outside lock - this is slow)
        start = settings.start_time
        duration = (settings.end_time or 30.0) - start
        features = analyze_audio(audio_path, start_time=start, duration=duration)
        
        # Determine which toggle system to use
        if settings.effect_toggles:
            # New toggle-based system
            toggles = toggles_from_dict(settings.effect_toggles)
        elif session_effect_toggles:
            # Use session's stored toggles
            toggles = toggles_from_dict(session_effect_toggles)
        elif settings.motion_intensity is not None:
            # Legacy slider-based system (backwards compatibility)
            toggles = legacy_settings_to_toggles(
                settings.motion_intensity / 100.0,
                settings.beat_reactivity / 100.0 if settings.beat_reactivity else 0.5,
                settings.energy_level / 100.0 if settings.energy_level else 0.5
            )
        else:
            # Default toggles
            toggles = EffectToggles()
        
        # Build image context if analysis exists
        image_context = None
        if session_image_analysis:
            image_context = image_context_from_dict(session_image_analysis)
        
        # Calculate effect parameters
        effect_params = calculate_effect_parameters(features, toggles, image_context)
        
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
            fps=24,
            quality="medium",
            duration=duration,
            preview=True
        )
        
        def progress_callback(progress: float):
            with session_lock:
                if session_id in sessions:
                    sessions[session_id].render_progress = progress
        
        render_video(
            image_path=image_path,
            audio_path=audio_path,
            output_path=str(output_path),
            effect_params=effect_params,
            render_settings=render_settings,
            audio_start=start,
            progress_callback=progress_callback,
            custom_particle_sprite=particle_sprite_path
        )
        
        # Generate playbook summary
        playbook = generate_playbook_v2(toggles, features, session_image_analysis)
        
        # Update session with results (with lock)
        with session_lock:
            if session_id in sessions:
                sessions[session_id].output_path = str(output_path)
                sessions[session_id].render_status = "complete"
                sessions[session_id].render_progress = 1.0
                sessions[session_id].playbook = playbook
        
    except Exception as e:
        with session_lock:
            if session_id in sessions:
                sessions[session_id].render_status = "error"
                sessions[session_id].playbook = {"error": str(e)}
        print(f"Render error: {e}")
        import traceback
        traceback.print_exc()


def generate_playbook_v2(
    toggles: EffectToggles,
    features: AudioFeatures,
    image_analysis: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate a summary of the effect settings."""
    active_effects = []
    
    effect_names = {
        "element_glow": "Element Glow",
        "element_scale": "Scale Pulse",
        "neon_outline": "Neon Outline",
        "echo_trail": "Echo Trail",
        "particle_burst": "Particle Burst",
        "energy_trails": "Energy Trails",
        "light_flares": "Light Flares",
        "glitch": "Glitch",
        "ripple_wave": "Ripple Wave",
        "film_grain": "Film Grain",
        "strobe_flash": "Strobe Flash",
        "vignette_pulse": "Vignette Pulse",
        "background_dim": "Background Dim"
    }
    
    for attr_name, display_name in effect_names.items():
        toggle = getattr(toggles, attr_name, None)
        if toggle and toggle.enabled:
            active_effects.append(f"{display_name} ({int(toggle.intensity * 100)}%)")
    
    # Build summary
    subject = "your image"
    if image_analysis:
        subject = image_analysis.get("subject", "your image")
    
    return {
        "summary": f"Created a beat-reactive visualization of {subject} with {len(active_effects)} active effects.",
        "active_effects": active_effects,
        "audio_info": {
            "tempo": round(features.tempo, 1),
            "beat_count": len(features.beat_times),
            "onset_density": round(features.onset_density, 1),
            "average_energy": round(features.average_energy, 2)
        },
        "image_info": {
            "subject": image_analysis.get("subject") if image_analysis else None,
            "mood": image_analysis.get("mood") if image_analysis else None,
            "colors": image_analysis.get("colors", [])[:3] if image_analysis else []
        }
    }


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
    
    if request.effect_toggles:
        session.effect_toggles = request.effect_toggles
    
    if request.resolution_scale is not None:
        session.resolution_scale = request.resolution_scale
    
    # Legacy support
    if request.motion_intensity is not None:
        session.motion_intensity = request.motion_intensity
    if request.beat_reactivity is not None:
        session.beat_reactivity = request.beat_reactivity
    if request.energy_level is not None:
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


# ============================================================================
# Export Endpoints
# ============================================================================

def export_video_task(session_id: str, quality: str, resolution_scale: Optional[float] = None):
    """Background task to export video at full quality."""
    try:
        # Get session data with lock
        with session_lock:
            if session_id not in sessions:
                print(f"Session {session_id} not found, aborting export")
                return
            session = sessions[session_id]
            session.render_status = "exporting"
            session.render_progress = 0.0
            # Copy needed data while holding lock
            audio_path = session.audio_path
            image_path = session.image_path
            start = session.start_time
            end_time = session.end_time
            session_effect_toggles = session.effect_toggles
            session_image_analysis = session.image_analysis
            session_aspect_ratio = session.aspect_ratio
            session_resolution_scale = resolution_scale if resolution_scale is not None else session.resolution_scale
            motion_intensity = session.motion_intensity
            beat_reactivity = session.beat_reactivity
            energy_level = session.energy_level
            particle_sprite_path = session.particle_sprite_path
        
        # Analyze audio (outside lock - this is slow)
        duration = (end_time or 30.0) - start
        features = analyze_audio(audio_path, start_time=start, duration=duration)
        
        # Get toggles
        if session_effect_toggles:
            toggles = toggles_from_dict(session_effect_toggles)
        else:
            toggles = legacy_settings_to_toggles(
                motion_intensity / 100.0,
                beat_reactivity / 100.0,
                energy_level / 100.0
            )
        
        # Build image context
        image_context = None
        if session_image_analysis:
            image_context = image_context_from_dict(session_image_analysis)
        
        effect_params = calculate_effect_parameters(features, toggles, image_context)
        
        # Parse aspect ratio
        aspect_map = {
            "9:16": AspectRatio.VERTICAL,
            "1:1": AspectRatio.SQUARE,
            "16:9": AspectRatio.HORIZONTAL,
            "4:5": AspectRatio.PORTRAIT
        }
        aspect = aspect_map.get(session_aspect_ratio, AspectRatio.VERTICAL)
        
        # Render at full quality
        output_dir = OUTPUT_DIR / session_id
        output_dir.mkdir(exist_ok=True)
        export_path = output_dir / "export.mp4"
        
        render_settings = RenderSettings(
            aspect_ratio=aspect,
            fps=30,
            quality=quality,
            duration=duration,
            preview=False,
            resolution_scale=session_resolution_scale
        )
        
        def progress_callback(progress: float):
            with session_lock:
                if session_id in sessions:
                    sessions[session_id].render_progress = progress
        
        render_video(
            image_path=image_path,
            audio_path=audio_path,
            output_path=str(export_path),
            effect_params=effect_params,
            render_settings=render_settings,
            audio_start=start,
            progress_callback=progress_callback,
            custom_particle_sprite=particle_sprite_path
        )
        
        # Update session with results (with lock)
        with session_lock:
            if session_id in sessions:
                sessions[session_id].render_status = "export_complete"
                sessions[session_id].render_progress = 1.0
        
    except Exception as e:
        with session_lock:
            if session_id in sessions:
                sessions[session_id].render_status = "error"
        print(f"Export error: {e}")
        import traceback
        traceback.print_exc()


def _apply_export_settings(session: SessionData, request: ExportRequest) -> None:
    """Apply optional settings from export request to session."""
    if request.start_time is not None:
        session.start_time = request.start_time
    if request.end_time is not None:
        session.end_time = request.end_time
    if request.aspect_ratio is not None:
        session.aspect_ratio = request.aspect_ratio
    if request.effect_toggles is not None:
        session.effect_toggles = request.effect_toggles
    if request.resolution_scale is not None:
        session.resolution_scale = request.resolution_scale
    session.last_accessed = time.time()


@app.post("/export")
async def export_video(request: ExportRequest, background_tasks: BackgroundTasks):
    """Export final high-quality video (no prior generate required)."""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    with session_lock:
        session = sessions[request.session_id]

        if not session.image_path or not session.audio_path:
            raise HTTPException(status_code=400, detail="Missing image or audio files.")

        _apply_export_settings(session, request)
        session.render_status = "exporting"
        session.render_progress = 0.0

    background_tasks.add_task(
        export_video_task,
        request.session_id,
        request.quality,
        request.resolution_scale,
    )

    return {
        "message": "Export started",
        "session_id": request.session_id,
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
