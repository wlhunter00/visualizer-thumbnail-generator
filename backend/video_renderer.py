"""
Video Renderer Module
Generates beat-reactive videos using FFmpeg and Pillow.
"""

import os
import math
import random
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, List, Tuple

from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
import numpy as np

from effect_engine import EffectParameters, get_effect_value_at_time


class AspectRatio(Enum):
    VERTICAL = "9:16"    # 1080x1920
    SQUARE = "1:1"       # 1080x1080
    HORIZONTAL = "16:9"  # 1920x1080
    PORTRAIT = "4:5"     # 1080x1350


ASPECT_DIMENSIONS = {
    AspectRatio.VERTICAL: (1080, 1920),
    AspectRatio.SQUARE: (1080, 1080),
    AspectRatio.HORIZONTAL: (1920, 1080),
    AspectRatio.PORTRAIT: (1080, 1350),
}

# Preview uses half resolution for faster rendering
PREVIEW_DIMENSIONS = {
    AspectRatio.VERTICAL: (540, 960),
    AspectRatio.SQUARE: (540, 540),
    AspectRatio.HORIZONTAL: (960, 540),
    AspectRatio.PORTRAIT: (540, 675),
}


@dataclass
class RenderSettings:
    aspect_ratio: AspectRatio = AspectRatio.VERTICAL
    fps: int = 30
    quality: str = "medium"  # low, medium, high
    duration: float = 30.0
    preview: bool = False  # Enable fast preview mode (half res, faster algorithms)


def render_video(
    image_path: str,
    audio_path: str,
    output_path: str,
    effect_params: EffectParameters,
    render_settings: RenderSettings,
    audio_start: float = 0.0,
    progress_callback: Optional[Callable[[float], None]] = None
) -> str:
    """
    Render a beat-reactive video.
    
    Args:
        image_path: Path to the source image
        audio_path: Path to the audio file
        output_path: Path for the output video
        effect_params: Calculated effect parameters
        render_settings: Quality and format settings
        audio_start: Start time in audio file
        progress_callback: Optional callback for progress updates
    
    Returns:
        Path to the rendered video
    """
    # Get dimensions based on preview mode
    if render_settings.preview:
        width, height = PREVIEW_DIMENSIONS[render_settings.aspect_ratio]
        resampling = Image.Resampling.BILINEAR  # Faster for preview
    else:
        width, height = ASPECT_DIMENSIONS[render_settings.aspect_ratio]
        resampling = Image.Resampling.LANCZOS  # Higher quality for export
    
    fps = render_settings.fps
    duration = render_settings.duration
    total_frames = int(duration * fps)
    
    # Load and prepare base image
    base_image = Image.open(image_path).convert("RGBA")
    base_image = fit_image_to_frame(base_image, width, height, resampling)
    
    # Create temporary directory for frames
    with tempfile.TemporaryDirectory() as temp_dir:
        frame_pattern = os.path.join(temp_dir, "frame_%06d.png")
        
        # Initialize particle system
        particles = initialize_particles(width, height, effect_params.particles.density * 100 if effect_params.particles.enabled else 0)
        
        # Render each frame
        for frame_num in range(total_frames):
            time = frame_num / fps
            
            # Get effect values at this time
            effects = get_effect_value_at_time(effect_params, time)
            
            # Start with base image
            frame = base_image.copy()
            
            # Apply effects in order
            frame = apply_zoom(frame, effects.get("zoom_scale", 1.0), width, height, resampling)
            frame = apply_shake(frame, effects.get("shake_offset", (0, 0)), width, height)
            frame = apply_blur(frame, effects.get("blur_amount", 0))
            frame = apply_color_shift(
                frame,
                effects.get("color_warmth", 0),
                effects.get("color_brightness", 0),
                effects.get("color_saturation", 0)
            )
            
            # Apply overlay effects
            if effect_params.particles.enabled and effects.get("particle_density", 0) > 0:
                particles = update_particles(particles, width, height, effect_params.particles.speed)
                frame = apply_particles(
                    frame, 
                    particles, 
                    effects.get("particle_density", 0.5),
                    effects.get("particle_opacity", 0.3),
                    effect_params.particles.size_range
                )
            
            if effect_params.geometric.enabled and effects.get("geometric_intensity", 0) > 0:
                frame = apply_geometric(
                    frame,
                    effects.get("geometric_type", "lines"),
                    effects.get("geometric_intensity", 0),
                    effects.get("geometric_opacity", 0.2),
                    effect_params.geometric.complexity,
                    time
                )
            
            if effects.get("glitch_active", False):
                frame = apply_glitch(
                    frame,
                    effects.get("glitch_intensity", 0),
                    effects.get("chromatic_aberration", 0)
                )
            
            # Convert to RGB and save
            frame = frame.convert("RGB")
            frame_path = frame_pattern % frame_num
            frame.save(frame_path, "PNG")
            
            # Update progress
            if progress_callback:
                progress_callback(frame_num / total_frames * 0.8)  # 80% for frames
        
        # Combine frames with audio using FFmpeg
        if progress_callback:
            progress_callback(0.85)
        
        # Quality and encoding settings based on mode
        if render_settings.preview:
            crf = 28  # Lower quality for fast preview
            preset = "ultrafast"
        else:
            crf = {"low": 28, "medium": 23, "high": 18}.get(render_settings.quality, 23)
            preset = "slow"  # Better compression for final export
        
        # FFmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", frame_pattern,
            "-ss", str(audio_start),
            "-t", str(duration),
            "-i", audio_path,
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        if progress_callback:
            progress_callback(1.0)
    
    return output_path


def fit_image_to_frame(
    image: Image.Image, 
    width: int, 
    height: int,
    resampling: Image.Resampling = Image.Resampling.LANCZOS
) -> Image.Image:
    """Fit image to frame, cropping to fill while maintaining aspect ratio."""
    img_ratio = image.width / image.height
    frame_ratio = width / height
    
    if img_ratio > frame_ratio:
        # Image is wider - fit height, crop width
        new_height = height
        new_width = int(height * img_ratio)
    else:
        # Image is taller - fit width, crop height
        new_width = width
        new_height = int(width / img_ratio)
    
    # Resize
    resized = image.resize((new_width, new_height), resampling)
    
    # Center crop
    left = (new_width - width) // 2
    top = (new_height - height) // 2
    cropped = resized.crop((left, top, left + width, top + height))
    
    return cropped


def apply_zoom(
    image: Image.Image, 
    scale: float, 
    width: int, 
    height: int,
    resampling: Image.Resampling = Image.Resampling.LANCZOS
) -> Image.Image:
    """Apply zoom effect by scaling and cropping."""
    if abs(scale - 1.0) < 0.001:
        return image
    
    # Scale image
    new_width = int(image.width * scale)
    new_height = int(image.height * scale)
    
    scaled = image.resize((new_width, new_height), resampling)
    
    # Center crop back to original size
    left = (new_width - width) // 2
    top = (new_height - height) // 2
    
    # Ensure we don't go out of bounds
    left = max(0, left)
    top = max(0, top)
    
    cropped = scaled.crop((left, top, left + width, top + height))
    
    # If cropped is smaller than needed, paste onto canvas
    if cropped.size != (width, height):
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        paste_x = (width - cropped.width) // 2
        paste_y = (height - cropped.height) // 2
        canvas.paste(cropped, (paste_x, paste_y))
        return canvas
    
    return cropped


def apply_shake(image: Image.Image, offset: Tuple[float, float], width: int, height: int) -> Image.Image:
    """Apply shake effect by offsetting the image."""
    offset_x, offset_y = int(offset[0]), int(offset[1])
    
    if offset_x == 0 and offset_y == 0:
        return image
    
    # Create canvas and paste offset image
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    canvas.paste(image, (offset_x, offset_y))
    
    return canvas


def apply_blur(image: Image.Image, blur_amount: float) -> Image.Image:
    """Apply Gaussian blur."""
    if blur_amount < 0.1:
        return image
    
    return image.filter(ImageFilter.GaussianBlur(radius=blur_amount))


def apply_color_shift(
    image: Image.Image, 
    warmth: float, 
    brightness: float, 
    saturation: float
) -> Image.Image:
    """Apply color adjustments."""
    result = image
    
    # Brightness
    if abs(brightness) > 0.01:
        enhancer = ImageEnhance.Brightness(result)
        result = enhancer.enhance(1.0 + brightness)
    
    # Saturation
    if abs(saturation) > 0.01:
        enhancer = ImageEnhance.Color(result)
        result = enhancer.enhance(1.0 + saturation)
    
    # Warmth (adjust color channels)
    if abs(warmth) > 0.01:
        r, g, b, a = result.split() if result.mode == "RGBA" else (*result.split(), None)
        
        # Warm = more red/yellow, Cool = more blue
        r_adjust = int(warmth * 30)
        b_adjust = int(-warmth * 20)
        
        r = r.point(lambda x: min(255, max(0, x + r_adjust)))
        b = b.point(lambda x: min(255, max(0, x + b_adjust)))
        
        if a:
            result = Image.merge("RGBA", (r, g, b, a))
        else:
            result = Image.merge("RGB", (r, g, b))
    
    return result


def initialize_particles(width: int, height: int, count: int) -> List[dict]:
    """Initialize particle positions."""
    particles = []
    for _ in range(int(count)):
        particles.append({
            "x": random.random() * width,
            "y": random.random() * height,
            "vx": (random.random() - 0.5) * 2,
            "vy": -random.random() * 2 - 0.5,  # Drift upward
            "size": random.random(),
            "alpha": random.random() * 0.5 + 0.3
        })
    return particles


def update_particles(particles: List[dict], width: int, height: int, speed: float) -> List[dict]:
    """Update particle positions."""
    for p in particles:
        p["x"] += p["vx"] * speed
        p["y"] += p["vy"] * speed
        
        # Wrap around
        if p["x"] < 0:
            p["x"] = width
        elif p["x"] > width:
            p["x"] = 0
        
        if p["y"] < 0:
            p["y"] = height
            p["x"] = random.random() * width
        elif p["y"] > height:
            p["y"] = 0
    
    return particles


def apply_particles(
    image: Image.Image,
    particles: List[dict],
    density: float,
    opacity: float,
    size_range: Tuple[float, float]
) -> Image.Image:
    """Draw particles on image."""
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    visible_count = int(len(particles) * density)
    
    for i, p in enumerate(particles[:visible_count]):
        size = size_range[0] + p["size"] * (size_range[1] - size_range[0])
        alpha = int(p["alpha"] * opacity * 255)
        
        x, y = int(p["x"]), int(p["y"])
        r = int(size / 2)
        
        # Draw soft particle
        draw.ellipse(
            [x - r, y - r, x + r, y + r],
            fill=(255, 255, 255, alpha)
        )
    
    return Image.alpha_composite(image, overlay)


def apply_geometric(
    image: Image.Image,
    shape_type: str,
    intensity: float,
    opacity: float,
    complexity: float,
    time: float
) -> Image.Image:
    """Draw geometric shapes on image."""
    if intensity < 0.05:
        return image
    
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    width, height = image.size
    alpha = int(opacity * intensity * 255)
    color = (255, 255, 255, alpha)
    
    num_shapes = int(5 + complexity * 15)
    
    if shape_type == "lines":
        for i in range(num_shapes):
            angle = (i / num_shapes) * math.pi + time * 0.5
            cx, cy = width // 2, height // 2
            length = min(width, height) * 0.4
            
            x1 = cx + math.cos(angle) * length
            y1 = cy + math.sin(angle) * length
            x2 = cx - math.cos(angle) * length
            y2 = cy - math.sin(angle) * length
            
            draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
    
    elif shape_type == "circles":
        for i in range(num_shapes):
            radius = (i + 1) / num_shapes * min(width, height) * 0.3 * intensity
            cx, cy = width // 2, height // 2
            
            draw.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                outline=color,
                width=2
            )
    
    elif shape_type == "grid":
        spacing = int(50 / (complexity + 0.1))
        offset = int((time * 20) % spacing)
        
        # Vertical lines
        for x in range(-offset, width + spacing, spacing):
            draw.line([(x, 0), (x, height)], fill=color, width=1)
        
        # Horizontal lines
        for y in range(-offset, height + spacing, spacing):
            draw.line([(0, y), (width, y)], fill=color, width=1)
    
    return Image.alpha_composite(image, overlay)


def apply_glitch(image: Image.Image, intensity: float, chromatic_aberration: float) -> Image.Image:
    """Apply glitch effects."""
    if intensity < 0.05:
        return image
    
    result = image.copy()
    
    # Chromatic aberration (RGB split)
    if chromatic_aberration > 0.5:
        offset = int(chromatic_aberration * intensity)
        
        r, g, b = result.convert("RGB").split()
        
        # Shift red channel left, blue channel right
        r_shifted = Image.new("L", r.size, 0)
        r_shifted.paste(r, (-offset, 0))
        
        b_shifted = Image.new("L", b.size, 0)
        b_shifted.paste(b, (offset, 0))
        
        result = Image.merge("RGB", (r_shifted, g, b_shifted))
        
        if image.mode == "RGBA":
            result = result.convert("RGBA")
            result.putalpha(image.split()[3])
    
    # Random horizontal slice displacement
    if intensity > 0.3:
        width, height = result.size
        num_slices = int(3 + intensity * 5)
        
        for _ in range(num_slices):
            y = random.randint(0, height - 20)
            slice_height = random.randint(5, 20)
            displacement = random.randint(-20, 20)
            
            slice_region = result.crop((0, y, width, y + slice_height))
            result.paste(slice_region, (displacement, y))
    
    return result

