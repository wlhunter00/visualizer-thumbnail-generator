"""
Image Analysis Module
Uses OpenAI's vision capabilities to analyze cover art and generate personalized effects.
"""

import os
import json
import base64
import httpx
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


@dataclass
class SubjectBounds:
    """Bounding box for detected subject as percentages (0-1)."""
    x: float  # Left edge
    y: float  # Top edge
    w: float  # Width
    h: float  # Height
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get center point of bounds."""
        return (self.x + self.w / 2, self.y + self.h / 2)


@dataclass
class GlowPoint:
    """A point in the image that should emit light/glow."""
    x: float  # X position (0-1)
    y: float  # Y position (0-1)
    intensity: float = 1.0  # Glow intensity (0-1)


@dataclass
class ImageAnalysis:
    """Results from AI image analysis."""
    subject: str  # What the main subject is (e.g., "light bulb", "guitar")
    subject_description: str  # More detailed description
    bounds: SubjectBounds  # Where the subject is located
    glow_points: List[GlowPoint]  # Points that should emit light
    colors: List[str]  # Dominant colors as hex codes
    mood: str  # Overall mood (warm, cool, energetic, calm, dark, etc.)
    suggested_particle_style: str  # What kind of particles would fit


@dataclass
class EffectSuggestion:
    """Suggested effect settings based on image and audio analysis."""
    # Element effects
    element_glow: Dict[str, Any] = field(default_factory=lambda: {"enabled": True, "intensity": 0.5})
    element_scale: Dict[str, Any] = field(default_factory=lambda: {"enabled": True, "intensity": 0.3})
    neon_outline: Dict[str, Any] = field(default_factory=lambda: {"enabled": False, "intensity": 0.5})
    echo_trail: Dict[str, Any] = field(default_factory=lambda: {"enabled": False, "intensity": 0.4})
    
    # Particle effects
    particle_burst: Dict[str, Any] = field(default_factory=lambda: {"enabled": True, "intensity": 0.5})
    energy_trails: Dict[str, Any] = field(default_factory=lambda: {"enabled": False, "intensity": 0.4})
    light_flares: Dict[str, Any] = field(default_factory=lambda: {"enabled": False, "intensity": 0.3})
    
    # Style effects
    glitch: Dict[str, Any] = field(default_factory=lambda: {"enabled": False, "intensity": 0.3})
    ripple_wave: Dict[str, Any] = field(default_factory=lambda: {"enabled": False, "intensity": 0.4})
    film_grain: Dict[str, Any] = field(default_factory=lambda: {"enabled": False, "intensity": 0.2})
    strobe_flash: Dict[str, Any] = field(default_factory=lambda: {"enabled": False, "intensity": 0.3})
    vignette_pulse: Dict[str, Any] = field(default_factory=lambda: {"enabled": True, "intensity": 0.4})
    
    # Background
    background_dim: Dict[str, Any] = field(default_factory=lambda: {"enabled": True, "intensity": 0.3})


def encode_image_to_base64(image_path: str) -> str:
    """Read an image file and encode it as base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_mime_type(image_path: str) -> str:
    """Get the MIME type based on file extension."""
    ext = Path(image_path).suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return mime_types.get(ext, "image/jpeg")


async def analyze_image(image_path: str) -> ImageAnalysis:
    """
    Analyze an image using OpenAI's vision capabilities.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        ImageAnalysis with detected subject, bounds, colors, etc.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in environment")
    
    # Encode image
    image_data = encode_image_to_base64(image_path)
    mime_type = get_image_mime_type(image_path)
    
    prompt = """Analyze this image for a music visualizer. Return a JSON object with these fields:

{
    "subject": "brief name of the main subject/element (e.g., 'light bulb', 'person', 'guitar')",
    "subject_description": "more detailed description of the subject and its visual characteristics",
    "bounds": {
        "x": 0.3,  // left edge as percentage (0-1) of image width
        "y": 0.2,  // top edge as percentage (0-1) of image height
        "w": 0.4,  // width as percentage of image width
        "h": 0.5   // height as percentage of image height
    },
    "glow_points": [
        {"x": 0.5, "y": 0.35, "intensity": 1.0}  // points that emit light (e.g., bulb filament, eyes, light sources)
    ],
    "colors": ["#FFD700", "#1A1A2E", "#FF6B35"],  // 3-5 dominant colors as hex codes
    "mood": "warm",  // one of: warm, cool, energetic, calm, dark, bright, mysterious, playful
    "suggested_particle_style": "glowing embers"  // what kind of particles would suit this image
}

Be precise with the bounds - they should tightly fit the main subject.
Identify any light sources or bright areas for glow_points.
Extract the most visually impactful colors.
Return ONLY the JSON, no other text."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            OPENAI_API_URL,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-5.2",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                "max_completion_tokens": 1000,
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Parse JSON from response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        data = json.loads(content.strip())
        
        return ImageAnalysis(
            subject=data["subject"],
            subject_description=data.get("subject_description", data["subject"]),
            bounds=SubjectBounds(
                x=data["bounds"]["x"],
                y=data["bounds"]["y"],
                w=data["bounds"]["w"],
                h=data["bounds"]["h"]
            ),
            glow_points=[
                GlowPoint(x=gp["x"], y=gp["y"], intensity=gp.get("intensity", 1.0))
                for gp in data.get("glow_points", [])
            ],
            colors=data["colors"],
            mood=data["mood"],
            suggested_particle_style=data.get("suggested_particle_style", "sparkles")
        )


async def generate_particle_sprite(
    colors: List[str],
    style: str,
    output_path: str
) -> str:
    """
    Generate a custom particle sprite using OpenAI's image generation.
    
    Args:
        colors: List of hex colors to use
        style: Description of particle style (e.g., "glowing embers", "musical notes")
        output_path: Where to save the generated sprite
        
    Returns:
        Path to the generated sprite image
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in environment")
    
    # Create color description
    color_desc = ", ".join(colors[:3]) if colors else "white, gold"
    
    prompt = f"""Create a single particle sprite for a music visualizer.
Style: {style}
Colors: {color_desc}

Requirements:
- Single small particle/element, centered
- Transparent/black background
- Glowing, luminous appearance
- Soft edges that fade out
- Size: small, suitable for many copies
- Abstract and ethereal, not photorealistic"""

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-image-1.5",
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024",
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
        
        result = response.json()
        image_data = result["data"][0]["b64_json"]
        
        # Save the image
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(image_data))
        
        return output_path


async def auto_suggest_effects(
    image_analysis: ImageAnalysis,
    audio_metrics: Dict[str, float]
) -> EffectSuggestion:
    """
    Use AI to suggest effect settings based on image analysis and audio metrics.
    
    Args:
        image_analysis: Results from analyze_image()
        audio_metrics: Raw audio metrics dict with keys like:
            - tempo: BPM
            - onset_density: hits per second
            - average_bass: 0-1
            - average_mid: 0-1
            - average_high: 0-1
            - dynamic_range: 0-1
            - beat_strength_variance: variance of beat strengths
            - average_energy: 0-1
            
    Returns:
        EffectSuggestion with recommended settings
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in environment")
    
    prompt = f"""You are an expert music visualizer designer. Based on the image and audio characteristics below, suggest which visual effects to enable and at what intensity.

IMAGE ANALYSIS:
- Subject: {image_analysis.subject}
- Description: {image_analysis.subject_description}
- Mood: {image_analysis.mood}
- Has glow points: {len(image_analysis.glow_points) > 0}
- Dominant colors: {', '.join(image_analysis.colors)}
- Suggested particle style: {image_analysis.suggested_particle_style}

AUDIO METRICS (raw data - interpret these yourself, don't assume BPM alone indicates energy):
- Tempo: {audio_metrics.get('tempo', 120)} BPM
- Onset density: {audio_metrics.get('onset_density', 5):.1f} hits/sec
- Bass energy: {audio_metrics.get('average_bass', 0.5):.2f} (0-1)
- Mid energy: {audio_metrics.get('average_mid', 0.5):.2f} (0-1)
- High energy: {audio_metrics.get('average_high', 0.5):.2f} (0-1)
- Dynamic range: {audio_metrics.get('dynamic_range', 0.5):.2f}
- Beat strength variance: {audio_metrics.get('beat_strength_variance', 0.1):.3f}
- Average energy: {audio_metrics.get('average_energy', 0.5):.2f}

AVAILABLE EFFECTS:
1. element_glow - Subject emits pulsating light (good for light sources, faces, focal points)
2. element_scale - Subject grows/shrinks with beat (subtle, adds life)
3. neon_outline - Glowing edge around subject (cyberpunk, bold)
4. echo_trail - Afterimage effect (motion, dreamy)
5. particle_burst - Particles explode from subject on beats (energetic, celebratory)
6. energy_trails - Glowing lines orbit subject (mystical, flowing)
7. light_flares - Lens flare from glow points (cinematic, dramatic)
8. glitch - RGB split, chromatic aberration (edgy, electronic)
9. ripple_wave - Distortion waves from subject (impactful, bass-heavy)
10. film_grain - VHS/retro texture (nostalgic, lo-fi)
11. strobe_flash - Brief flashes on strong beats (intense, use sparingly)
12. vignette_pulse - Dark edges pulse with rhythm (focus, atmosphere)
13. background_dim - Darken background to make subject pop (contrast)

Return a JSON object where each effect has "enabled" (boolean) and "intensity" (0.0-1.0):

{{
    "element_glow": {{"enabled": true, "intensity": 0.7}},
    "element_scale": {{"enabled": true, "intensity": 0.3}},
    "neon_outline": {{"enabled": false, "intensity": 0.5}},
    "echo_trail": {{"enabled": false, "intensity": 0.4}},
    "particle_burst": {{"enabled": true, "intensity": 0.6}},
    "energy_trails": {{"enabled": true, "intensity": 0.5}},
    "light_flares": {{"enabled": false, "intensity": 0.3}},
    "glitch": {{"enabled": false, "intensity": 0.3}},
    "ripple_wave": {{"enabled": false, "intensity": 0.4}},
    "film_grain": {{"enabled": false, "intensity": 0.2}},
    "strobe_flash": {{"enabled": false, "intensity": 0.3}},
    "vignette_pulse": {{"enabled": true, "intensity": 0.4}},
    "background_dim": {{"enabled": true, "intensity": 0.3}}
}}

Consider:
- If image has glow points, enable light_flares and element_glow
- High onset density = more reactive effects (particle_burst, glitch)
- High bass = ripple_wave, strong scale
- High highs = sparkly particles, light effects
- Dark mood = vignette, dim background, subtle effects
- Energetic mood = more enabled effects, higher intensities
- Don't enable everything - be selective for a cohesive look

Return ONLY the JSON, no explanation."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            OPENAI_API_URL,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-5.2",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_completion_tokens": 800,
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Parse JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        data = json.loads(content.strip())
        
        return EffectSuggestion(
            element_glow=data.get("element_glow", {"enabled": True, "intensity": 0.5}),
            element_scale=data.get("element_scale", {"enabled": True, "intensity": 0.3}),
            neon_outline=data.get("neon_outline", {"enabled": False, "intensity": 0.5}),
            echo_trail=data.get("echo_trail", {"enabled": False, "intensity": 0.4}),
            particle_burst=data.get("particle_burst", {"enabled": True, "intensity": 0.5}),
            energy_trails=data.get("energy_trails", {"enabled": False, "intensity": 0.4}),
            light_flares=data.get("light_flares", {"enabled": False, "intensity": 0.3}),
            glitch=data.get("glitch", {"enabled": False, "intensity": 0.3}),
            ripple_wave=data.get("ripple_wave", {"enabled": False, "intensity": 0.4}),
            film_grain=data.get("film_grain", {"enabled": False, "intensity": 0.2}),
            strobe_flash=data.get("strobe_flash", {"enabled": False, "intensity": 0.3}),
            vignette_pulse=data.get("vignette_pulse", {"enabled": True, "intensity": 0.4}),
            background_dim=data.get("background_dim", {"enabled": True, "intensity": 0.3})
        )


def image_analysis_to_dict(analysis: ImageAnalysis) -> Dict[str, Any]:
    """Convert ImageAnalysis to a JSON-serializable dict."""
    return {
        "subject": analysis.subject,
        "subject_description": analysis.subject_description,
        "bounds": {
            "x": analysis.bounds.x,
            "y": analysis.bounds.y,
            "w": analysis.bounds.w,
            "h": analysis.bounds.h
        },
        "glow_points": [
            {"x": gp.x, "y": gp.y, "intensity": gp.intensity}
            for gp in analysis.glow_points
        ],
        "colors": analysis.colors,
        "mood": analysis.mood,
        "suggested_particle_style": analysis.suggested_particle_style
    }


def effect_suggestion_to_dict(suggestion: EffectSuggestion) -> Dict[str, Any]:
    """Convert EffectSuggestion to a JSON-serializable dict."""
    return {
        "element_glow": suggestion.element_glow,
        "element_scale": suggestion.element_scale,
        "neon_outline": suggestion.neon_outline,
        "echo_trail": suggestion.echo_trail,
        "particle_burst": suggestion.particle_burst,
        "energy_trails": suggestion.energy_trails,
        "light_flares": suggestion.light_flares,
        "glitch": suggestion.glitch,
        "ripple_wave": suggestion.ripple_wave,
        "film_grain": suggestion.film_grain,
        "strobe_flash": suggestion.strobe_flash,
        "vignette_pulse": suggestion.vignette_pulse,
        "background_dim": suggestion.background_dim
    }

