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
from effect_schema import (
    EFFECT_KEYS,
    build_example_json,
    build_prompt_effect_docs,
    default_effect_toggle,
    default_suggestion_dict,
    normalize_suggestion,
)
from export_history import build_few_shot_examples_section, find_similar_exports

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
    element_glow: Dict[str, Any] = field(default_factory=lambda: default_effect_toggle("element_glow"))
    element_scale: Dict[str, Any] = field(default_factory=lambda: default_effect_toggle("element_scale"))
    neon_outline: Dict[str, Any] = field(default_factory=lambda: default_effect_toggle("neon_outline"))
    particle_burst: Dict[str, Any] = field(default_factory=lambda: default_effect_toggle("particle_burst"))
    energy_trails: Dict[str, Any] = field(default_factory=lambda: default_effect_toggle("energy_trails"))
    light_flares: Dict[str, Any] = field(default_factory=lambda: default_effect_toggle("light_flares"))
    glitch: Dict[str, Any] = field(default_factory=lambda: default_effect_toggle("glitch"))
    ripple_wave: Dict[str, Any] = field(default_factory=lambda: default_effect_toggle("ripple_wave"))
    film_grain: Dict[str, Any] = field(default_factory=lambda: default_effect_toggle("film_grain"))
    strobe_flash: Dict[str, Any] = field(default_factory=lambda: default_effect_toggle("strobe_flash"))
    vignette_pulse: Dict[str, Any] = field(default_factory=lambda: default_effect_toggle("vignette_pulse"))
    background_dim: Dict[str, Any] = field(default_factory=lambda: default_effect_toggle("background_dim"))


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
    audio_metrics: Dict[str, float],
    aspect_ratio: str = "9:16",
) -> Dict[str, Any]:
    """
    Use AI to suggest effect settings based on image analysis and audio metrics.

    Returns canonical effect_toggles dict (enabled, intensity, trigger_source, radius).
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in environment")

    similar = find_similar_exports(audio_metrics, image_analysis, k=3, aspect_ratio=aspect_ratio)
    few_shot = build_few_shot_examples_section(similar)
    effect_docs = build_prompt_effect_docs()
    example_json = build_example_json()

    prompt = f"""You are an expert music visualizer designer. Based on the image and audio characteristics below, suggest effect settings using ALL available levers per effect.

IMAGE ANALYSIS:
- Subject: {image_analysis.subject}
- Description: {image_analysis.subject_description}
- Mood: {image_analysis.mood}
- Subject bounds (0-1): x={image_analysis.bounds.x:.2f}, y={image_analysis.bounds.y:.2f}, w={image_analysis.bounds.w:.2f}, h={image_analysis.bounds.h:.2f}
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

{few_shot}

{effect_docs}

Return a JSON object with one key per effect. Each effect must include "enabled" and "intensity".
For beat-reactive effects, include "trigger_source" when enabled.
For background_dim when enabled, include "radius" (0-1): tight/small subject → lower radius (~0.35), subject fills frame → higher (~0.65).

Example response shape:
{example_json}

Consider:
- If image has glow points, enable light_flares and element_glow
- High onset density = more reactive effects (particle_burst, glitch with onsets)
- High bass = ripple_wave with low trigger, strong scale with low trigger
- High highs = light_flares/strobe with high trigger, sparkly particles
- Dark mood = vignette, dim background, subtle effects
- Energetic mood = more enabled effects, higher intensities
- Match trigger_source to the dominant frequency content of the track
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
                "max_completion_tokens": 1200,
            }
        )

        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        try:
            data = json.loads(content.strip())
        except json.JSONDecodeError:
            data = default_suggestion_dict()

    normalized = normalize_suggestion(data, audio_metrics, image_analysis)

    from effect_engine import toggles_from_dict, toggles_to_dict
    return toggles_to_dict(toggles_from_dict(normalized))


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
    return {key: getattr(suggestion, key) for key in EFFECT_KEYS}


# ============================================================================
# Image Transformation
# ============================================================================

async def transform_image(
    image_path: str,
    prompt: str,
    output_path: str
) -> str:
    """
    Transform an image using OpenAI's DALL-E image editing API.
    
    Args:
        image_path: Path to the source image file
        prompt: Transformation prompt describing how to modify the image
        output_path: Where to save the transformed image
        
    Returns:
        Path to the transformed image
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in environment")
    
    # Read and encode the source image
    image_data = encode_image_to_base64(image_path)
    mime_type = get_image_mime_type(image_path)
    
    # For DALL-E image editing, we need to use the images/edits endpoint
    # But since we want full transformation, we'll use GPT-4o vision to 
    # understand the image and then generate a new one via DALL-E
    
    # First, analyze the image to get a description
    analysis_prompt = """Describe this image in detail for recreation. Include:
- Main subject(s) and their positioning
- Color palette and lighting
- Style and mood
- Background elements
- Any text visible in the image

Be specific but concise. This description will be used to recreate the image with modifications."""

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Analyze the original image
        analysis_response = await client.post(
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
                            {"type": "text", "text": analysis_prompt},
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
                "max_completion_tokens": 500,
            }
        )
        
        if analysis_response.status_code != 200:
            raise Exception(f"Image analysis failed: {analysis_response.status_code} - {analysis_response.text}")
        
        analysis_result = analysis_response.json()
        image_description = analysis_result["choices"][0]["message"]["content"]
        
        # Step 2: Generate transformed image with DALL-E
        # Combine the image description with the transformation prompt
        generation_prompt = f"""Based on this original image:
{image_description}

Apply these transformations:
{prompt}

Create a high-quality 1:1 square image that faithfully represents the original subject with the requested style modifications applied."""

        generation_response = await client.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-image-1.5",
                "prompt": generation_prompt,
                "n": 1,
                "size": "1024x1024",
                "quality": "hd",
            }
        )
        
        if generation_response.status_code != 200:
            raise Exception(f"Image generation failed: {generation_response.status_code} - {generation_response.text}")
        
        generation_result = generation_response.json()
        
        # Handle both b64_json and url response formats
        if "b64_json" in generation_result["data"][0]:
            transformed_data = generation_result["data"][0]["b64_json"]
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(transformed_data))
        else:
            # If URL is returned, download the image
            image_url = generation_result["data"][0]["url"]
            image_response = await client.get(image_url)
            with open(output_path, "wb") as f:
                f.write(image_response.content)
        
        return output_path

