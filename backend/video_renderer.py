"""
Video Renderer Module
Generates beat-reactive videos with 13 customizable effects using layer compositing.
"""

import os
import math
import random
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, List, Tuple, Dict, Any

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
    quality: str = "medium"
    duration: float = 30.0
    preview: bool = False


@dataclass
class Particle:
    """A single particle for burst effects."""
    x: float
    y: float
    vx: float
    vy: float
    size: float
    color: Tuple[int, int, int]
    alpha: float
    birth_time: float
    lifetime: float


class ParticleSystem:
    """Manages particle bursts."""
    
    def __init__(self):
        self.particles: List[Particle] = []
    
    def spawn_burst_from_bounds(
        self,
        bounds_x: float, bounds_y: float,
        bounds_w: float, bounds_h: float,
        count: int,
        colors: List[Tuple[int, int, int]],
        size_range: Tuple[float, float],
        speed: float,
        lifetime: float,
        time: float,
        width: int, height: int
    ):
        """Spawn particles from the perimeter of the subject's elliptical bounds."""
        # Calculate center and radii in pixels
        center_x = (bounds_x + bounds_w / 2) * width
        center_y = (bounds_y + bounds_h / 2) * height
        radius_x = (bounds_w / 2) * width * 1.1  # Slightly outside bounds
        radius_y = (bounds_h / 2) * height * 1.1
        
        for _ in range(count):
            # Random angle around the ellipse perimeter
            angle = random.random() * 2 * math.pi
            
            # Spawn position on ellipse perimeter
            spawn_x = center_x + math.cos(angle) * radius_x
            spawn_y = center_y + math.sin(angle) * radius_y
            
            # Velocity radiates outward from center
            velocity = speed * (0.5 + random.random() * 0.5)
            
            self.particles.append(Particle(
                x=spawn_x,
                y=spawn_y,
                vx=math.cos(angle) * velocity,
                vy=math.sin(angle) * velocity,
                size=random.uniform(size_range[0], size_range[1]),
                color=random.choice(colors),
                alpha=0.8 + random.random() * 0.2,
                birth_time=time,
                lifetime=lifetime * (0.7 + random.random() * 0.3)
            ))
    
    def update(self, time: float, dt: float):
        """Update particle positions and remove dead particles."""
        alive = []
        for p in self.particles:
            age = time - p.birth_time
            if age < p.lifetime:
                # Update position with gravity and drag
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.vy += 50 * dt  # Slight gravity
                p.vx *= 0.98  # Drag
                p.vy *= 0.98
                alive.append(p)
        self.particles = alive
    
    def draw(self, image: Image.Image, time: float) -> Image.Image:
        """Draw all particles onto the image."""
        if not self.particles:
            return image
        
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        for p in self.particles:
            age = time - p.birth_time
            progress = age / p.lifetime
            
            # Fade out as particle ages
            alpha = int(p.alpha * (1 - progress) * 255)
            if alpha <= 0:
                continue
            
            # Shrink as particle ages
            size = p.size * (1 - progress * 0.5)
            
            x, y = int(p.x), int(p.y)
            r = int(size / 2)
            
            if r > 0:
                color = (*p.color, alpha)
                draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
        
        return Image.alpha_composite(image, overlay)


def render_video(
    image_path: str,
    audio_path: str,
    output_path: str,
    effect_params: EffectParameters,
    render_settings: RenderSettings,
    audio_start: float = 0.0,
    progress_callback: Optional[Callable[[float], None]] = None,
    custom_particle_sprite: Optional[str] = None
) -> str:
    """
    Render a beat-reactive video with 13 customizable effects.
    
    Args:
        image_path: Path to the source image
        audio_path: Path to the audio file
        output_path: Path for the output video
        effect_params: Calculated effect parameters
        render_settings: Quality and format settings
        audio_start: Start time in audio file
        progress_callback: Optional callback for progress updates
        custom_particle_sprite: Optional path to custom particle sprite image
    
    Returns:
        Path to the rendered video
    """
    # Get dimensions
    if render_settings.preview:
        width, height = PREVIEW_DIMENSIONS[render_settings.aspect_ratio]
        resampling = Image.Resampling.BILINEAR
    else:
        width, height = ASPECT_DIMENSIONS[render_settings.aspect_ratio]
        resampling = Image.Resampling.LANCZOS
    
    fps = render_settings.fps
    duration = render_settings.duration
    total_frames = int(duration * fps)
    
    # Load and prepare base image
    base_image = Image.open(image_path).convert("RGBA")
    base_image = fit_image_to_frame(base_image, width, height, resampling)
    
    # Load custom particle sprite if provided
    particle_sprite = None
    if custom_particle_sprite and os.path.exists(custom_particle_sprite):
        try:
            particle_sprite = Image.open(custom_particle_sprite).convert("RGBA")
        except Exception:
            pass
    
    # Initialize systems
    particle_system = ParticleSystem()
    previous_bursts = set()  # Track which bursts we've already spawned
    
    # Store echo trail frames
    echo_frames: List[Image.Image] = []
    
    with tempfile.TemporaryDirectory() as temp_dir:
        frame_pattern = os.path.join(temp_dir, "frame_%06d.png")
        
        for frame_num in range(total_frames):
            time = frame_num / fps
            dt = 1.0 / fps
            
            # Get effect values at this time
            effects = get_effect_value_at_time(effect_params, time)
            bounds = effects.get("subject_bounds", {})
            
            # Start with base image
            frame = base_image.copy()
            
            # ================================================================
            # LAYER 1: BACKGROUND WITH DIM AND BLUR
            # ================================================================
            if effects.get("background_dim_enabled", False):
                frame = apply_background_dim(
                    frame, bounds, 
                    effects.get("background_dim_amount", 0),
                    effects.get("background_blur", 0),
                    width, height
                )
            
            # ================================================================
            # LAYER 2: RIPPLE WAVE DISTORTION
            # ================================================================
            ripples = effects.get("ripple_waves", [])
            if ripples:
                for ripple in ripples:
                    frame = apply_ripple_wave(
                        frame, ripple, width, height,
                        effects.get("ripple_intensity", 0.5)
                    )
            
            # ================================================================
            # LAYER 3: ELEMENT SCALE
            # ================================================================
            scale = effects.get("element_scale", 1.0)
            if abs(scale - 1.0) > 0.001:
                frame = apply_element_scale(frame, bounds, scale, width, height, resampling)
            
            # ================================================================
            # LAYER 4: ELEMENT GLOW
            # ================================================================
            glow_intensity = effects.get("element_glow_intensity", 0)
            if glow_intensity > 0.01:
                frame = apply_element_glow(
                    frame, bounds,
                    glow_intensity,
                    effects.get("element_glow_radius", 50),
                    effects.get("element_glow_color", (255, 200, 100)),
                    width, height
                )
            
            # ================================================================
            # LAYER 5: NEON OUTLINE
            # ================================================================
            outline_intensity = effects.get("neon_outline_intensity", 0)
            if outline_intensity > 0.01:
                frame = apply_neon_outline(
                    frame, bounds,
                    outline_intensity,
                    effects.get("neon_outline_color", (0, 255, 255)),
                    effects.get("neon_outline_width", 3),
                    effects.get("neon_outline_glow", 10),
                    width, height
                )
            
            # ================================================================
            # LAYER 6: ECHO TRAIL
            # ================================================================
            # Store frame BEFORE applying echo (so we echo clean frames, not echoes of echoes)
            if effects.get("echo_trail_enabled", False):
                echo_frames.append(frame.copy())
                max_frames = effects.get("echo_trail_count", 5) + 2
                if len(echo_frames) > max_frames:
                    echo_frames.pop(0)
            elif echo_frames:
                # Clear accumulated frames when effect is disabled to free memory
                echo_frames.clear()
            
            # Now apply the echo trail effect
            if effects.get("echo_trail_enabled", False):
                frame = apply_echo_trail(
                    frame, echo_frames[:-1],  # Exclude current frame from echoes
                    effects.get("echo_trail_count", 5),
                    effects.get("echo_trail_decay", 0.7),
                    effects.get("echo_trail_intensity", 0.5)
                )
            
            # ================================================================
            # LAYER 7: PARTICLE BURST
            # ================================================================
            bursts = effects.get("particle_bursts", [])
            burst_params = effects.get("particle_burst_params", {})
            
            # Spawn new bursts from subject perimeter
            for i, burst in enumerate(bursts):
                burst_id = (burst.get("bounds_x", 0.25), burst.get("bounds_y", 0.25), i)
                if burst.get("progress", 0) < 0.1 and burst_id not in previous_bursts:
                    previous_bursts.add(burst_id)
                    particle_system.spawn_burst_from_bounds(
                        bounds_x=burst.get("bounds_x", 0.25),
                        bounds_y=burst.get("bounds_y", 0.25),
                        bounds_w=burst.get("bounds_w", 0.5),
                        bounds_h=burst.get("bounds_h", 0.5),
                        count=burst_params.get("count", 50),
                        colors=burst_params.get("colors", [(255, 255, 255), (255, 220, 180), (200, 220, 255)]),
                        size_range=burst_params.get("size_range", (3, 12)),
                        speed=burst_params.get("speed", 200),
                        lifetime=burst_params.get("lifetime", 1.0),
                        time=time,
                        width=width,
                        height=height
                    )
            
            # Update and draw particles
            particle_system.update(time, dt)
            frame = particle_system.draw(frame, time)
            
            # Clean up old burst IDs
            if len(previous_bursts) > 100:
                previous_bursts.clear()
            
            # ================================================================
            # LAYER 8: ENERGY TRAILS
            # ================================================================
            if effects.get("energy_trails_enabled", False):
                frame = apply_energy_trails(
                    frame,
                    effects.get("energy_trails_params", {}),
                    width, height
                )
            
            # ================================================================
            # LAYER 9: LIGHT FLARES
            # ================================================================
            flare_intensity = effects.get("light_flares_intensity", 0)
            if flare_intensity > 0.01:
                frame = apply_light_flares(
                    frame,
                    effects.get("light_flares_points", []),
                    flare_intensity,
                    effects.get("light_flares_size", 100),
                    effects.get("light_flares_colors", [(255, 255, 200)]),
                    width, height
                )
            
            # ================================================================
            # LAYER 10: GLITCH
            # ================================================================
            if effects.get("glitch_active", False):
                frame = apply_glitch(
                    frame,
                    effects.get("glitch_intensity", 0),
                    effects.get("glitch_chromatic", 0),
                    effects.get("glitch_rgb_split", 0),
                    effects.get("glitch_scan_lines", False),
                    effects.get("glitch_scan_opacity", 0),
                    effects.get("glitch_slice", False)
                )
            
            # ================================================================
            # LAYER 11: FILM GRAIN
            # ================================================================
            if effects.get("film_grain_enabled", False):
                frame = apply_film_grain(
                    frame,
                    effects.get("film_grain_intensity", 0.2),
                    effects.get("film_grain_size", 1.5)
                )
            
            # ================================================================
            # LAYER 12: STROBE FLASH
            # ================================================================
            if effects.get("strobe_active", False):
                frame = apply_strobe_flash(
                    frame,
                    effects.get("strobe_intensity", 0.5),
                    effects.get("strobe_color", (255, 255, 255))
                )
            
            # ================================================================
            # LAYER 13: VIGNETTE
            # ================================================================
            vignette_strength = effects.get("vignette_strength", 0)
            if vignette_strength > 0.01:
                frame = apply_vignette(frame, vignette_strength, width, height)
            
            # Convert to RGB and save
            frame = frame.convert("RGB")
            frame_path = frame_pattern % frame_num
            frame.save(frame_path, "PNG")
            
            if progress_callback:
                progress_callback(frame_num / total_frames * 0.8)
        
        # Combine frames with audio using FFmpeg
        if progress_callback:
            progress_callback(0.85)
        
        if render_settings.preview:
            crf = 28
            preset = "ultrafast"
        else:
            crf = {"low": 28, "medium": 23, "high": 18}.get(render_settings.quality, 23)
            preset = "slow"
        
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
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown FFmpeg error"
            raise RuntimeError(f"FFmpeg failed (exit code {result.returncode}): {error_msg}")
        
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
        new_height = height
        new_width = int(height * img_ratio)
    else:
        new_width = width
        new_height = int(width / img_ratio)
    
    resized = image.resize((new_width, new_height), resampling)
    
    left = (new_width - width) // 2
    top = (new_height - height) // 2
    cropped = resized.crop((left, top, left + width, top + height))
    
    return cropped


# ============================================================================
# EFFECT IMPLEMENTATIONS
# ============================================================================

def apply_background_dim(
    image: Image.Image,
    bounds: Dict[str, float],
    dim_amount: float,
    blur_amount: float,
    width: int, height: int
) -> Image.Image:
    """Dim and blur the background outside the subject bounds."""
    if dim_amount < 0.01 and blur_amount < 0.1:
        return image
    
    # Create darkened/blurred version
    bg = image.copy()
    
    if blur_amount > 0.1:
        bg = bg.filter(ImageFilter.GaussianBlur(radius=blur_amount))
    
    if dim_amount > 0.01:
        enhancer = ImageEnhance.Brightness(bg)
        bg = enhancer.enhance(1 - dim_amount)
    
    # Create mask for subject area (gradient for soft edges)
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    
    x = int(bounds.get("x", 0.25) * width)
    y = int(bounds.get("y", 0.25) * height)
    w = int(bounds.get("w", 0.5) * width)
    h = int(bounds.get("h", 0.5) * height)
    
    # Draw soft ellipse mask
    padding = int(min(w, h) * 0.2)
    draw.ellipse([x - padding, y - padding, x + w + padding, y + h + padding], fill=255)
    
    # Blur the mask for soft edges
    mask = mask.filter(ImageFilter.GaussianBlur(radius=padding))
    
    # Composite: bg where mask is 0, original where mask is 255
    return Image.composite(image, bg, mask)


def apply_ripple_wave(
    image: Image.Image,
    ripple: Dict[str, Any],
    width: int, height: int,
    intensity: float
) -> Image.Image:
    """Apply elliptical ripple wave distortion originating from subject bounds."""
    if intensity < 0.01:
        return image
    
    # Get bounds for elliptical ripple origin
    bounds_x = ripple.get("bounds_x", 0.25)
    bounds_y = ripple.get("bounds_y", 0.25)
    bounds_w = ripple.get("bounds_w", 0.5)
    bounds_h = ripple.get("bounds_h", 0.5)
    
    # Center of the ellipse in pixels
    center_x = (bounds_x + bounds_w / 2) * width
    center_y = (bounds_y + bounds_h / 2) * height
    
    # Ellipse radii (ripple starts from edge of subject)
    radius_x = (bounds_w / 2) * width
    radius_y = (bounds_h / 2) * height
    
    ripple_radius = ripple.get("radius", 100)  # How far the ripple has expanded
    amplitude = ripple.get("amplitude", 10) * intensity
    wavelength = ripple.get("wavelength", 50)
    
    if amplitude < 1:
        return image
    
    # Convert to numpy for faster processing
    img_array = np.array(image)
    
    # Create coordinate grids
    y_coords, x_coords = np.mgrid[0:height, 0:width].astype(np.float32)
    
    # Calculate normalized elliptical distance from center
    # Points on the ellipse have ellipse_dist = 1.0
    dx = (x_coords - center_x) / max(radius_x, 1)
    dy = (y_coords - center_y) / max(radius_y, 1)
    ellipse_dist = np.sqrt(dx * dx + dy * dy)
    
    # Convert to actual distance from ellipse edge
    # dist_from_edge = (ellipse_dist - 1.0) * average_radius
    avg_radius = (radius_x + radius_y) / 2
    dist_from_edge = (ellipse_dist - 1.0) * avg_radius
    
    # Angle for displacement direction
    angle = np.arctan2(y_coords - center_y, x_coords - center_x)
    
    # Create mask for affected pixels (ripple expands outward from ellipse edge)
    affected_mask = (dist_from_edge >= 0) & (np.abs(dist_from_edge - ripple_radius) < wavelength * 2)
    
    # Calculate displacement for all pixels (vectorized)
    wave = np.sin((dist_from_edge - ripple_radius) * 2 * np.pi / wavelength)
    gaussian_falloff = np.exp(-((dist_from_edge - ripple_radius) / wavelength) ** 2)
    displacement = wave * amplitude * gaussian_falloff
    
    # Apply displacement only where affected
    displacement = np.where(affected_mask, displacement, 0)
    
    # Calculate source coordinates
    src_x = (x_coords + np.cos(angle) * displacement).astype(np.int32)
    src_y = (y_coords + np.sin(angle) * displacement).astype(np.int32)
    
    # Clamp to valid range
    src_x = np.clip(src_x, 0, width - 1)
    src_y = np.clip(src_y, 0, height - 1)
    
    # Sample from source image using advanced indexing
    result = img_array[src_y, src_x]
    
    return Image.fromarray(result.astype('uint8'), mode=image.mode)


def apply_element_scale(
    image: Image.Image,
    bounds: Dict[str, float],
    scale: float,
    width: int, height: int,
    resampling: Image.Resampling
) -> Image.Image:
    """Scale the element area using an elliptical feathered mask for natural blending."""
    if abs(scale - 1.0) < 0.001:
        return image
    
    # Get bounds
    bx = int(bounds.get("x", 0.25) * width)
    by = int(bounds.get("y", 0.25) * height)
    bw = int(bounds.get("w", 0.5) * width)
    bh = int(bounds.get("h", 0.5) * height)
    
    # Expand bounds slightly for smoother effect
    padding = int(min(bw, bh) * 0.15)
    bx = max(0, bx - padding)
    by = max(0, by - padding)
    bw = min(width - bx, bw + padding * 2)
    bh = min(height - by, bh + padding * 2)
    
    # Calculate scaled dimensions
    new_w = int(bw * scale)
    new_h = int(bh * scale)
    
    if new_w <= 0 or new_h <= 0:
        return image
    
    # Create elliptical mask with soft feathered edges
    mask = Image.new("L", (bw, bh), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([0, 0, bw - 1, bh - 1], fill=255)
    
    # Apply Gaussian blur for soft feathered edges
    feather_amount = max(5, int(min(bw, bh) * 0.1))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=feather_amount))
    
    # Extract element region and apply elliptical mask as alpha
    element = image.crop((bx, by, bx + bw, by + bh)).convert("RGBA")
    element.putalpha(mask)
    
    # Scale the masked element
    scaled = element.resize((new_w, new_h), resampling)
    
    # Calculate position to center the scaled element
    center_x = bx + bw // 2
    center_y = by + bh // 2
    paste_x = center_x - new_w // 2
    paste_y = center_y - new_h // 2
    
    # Composite onto original image
    result = image.copy()
    result.paste(scaled, (paste_x, paste_y), scaled)
    
    return result


def apply_element_glow(
    image: Image.Image,
    bounds: Dict[str, float],
    intensity: float,
    radius: float,
    color: Tuple[int, int, int],
    width: int, height: int
) -> Image.Image:
    """Add a glow effect around the element."""
    if intensity < 0.01:
        return image
    
    # Create glow layer
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    
    cx = int(bounds.get("center_x", 0.5) * width)
    cy = int(bounds.get("center_y", 0.5) * height)
    bw = int(bounds.get("w", 0.5) * width)
    bh = int(bounds.get("h", 0.5) * height)
    
    # Draw multiple ellipses for glow
    for i in range(int(radius), 0, -5):
        alpha = int(intensity * 100 * (i / radius))
        glow_color = (*color, min(255, alpha))
        
        rx = bw // 2 + i
        ry = bh // 2 + i
        
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=glow_color)
    
    # Blur the glow
    glow = glow.filter(ImageFilter.GaussianBlur(radius=radius / 3))
    
    return Image.alpha_composite(image, glow)


def apply_neon_outline(
    image: Image.Image,
    bounds: Dict[str, float],
    intensity: float,
    color: Tuple[int, int, int],
    line_width: float,
    glow_radius: float,
    width: int, height: int
) -> Image.Image:
    """Draw a neon outline tracing the actual edges of the subject."""
    if intensity < 0.01:
        return image
    
    # Convert to numpy for edge detection
    img_array = np.array(image.convert("RGB"))
    
    # Convert to grayscale for edge detection
    gray = np.mean(img_array, axis=2).astype(np.uint8)
    
    # Apply Sobel edge detection
    # Sobel kernels for x and y gradients
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)
    
    # Pad image for convolution
    padded = np.pad(gray.astype(np.float32), 1, mode='edge')
    
    # Manual convolution for edge detection
    gx = np.zeros_like(gray, dtype=np.float32)
    gy = np.zeros_like(gray, dtype=np.float32)
    
    for i in range(3):
        for j in range(3):
            gx += sobel_x[i, j] * padded[i:i+gray.shape[0], j:j+gray.shape[1]]
            gy += sobel_y[i, j] * padded[i:i+gray.shape[0], j:j+gray.shape[1]]
    
    # Calculate edge magnitude
    edges = np.sqrt(gx**2 + gy**2)
    
    # Normalize and threshold edges
    edges = (edges / edges.max() * 255).astype(np.uint8) if edges.max() > 0 else edges.astype(np.uint8)
    
    # Apply threshold to get clean edges
    threshold = 30
    edge_mask = (edges > threshold).astype(np.uint8) * 255
    
    # Create edge image from the mask
    edge_img = Image.fromarray(edge_mask, mode='L')
    
    # Dilate the edges slightly to make them more visible
    edge_img = edge_img.filter(ImageFilter.MaxFilter(size=int(line_width) * 2 + 1))
    
    # Create the neon outline overlay
    outline_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    # Colorize the edges with the neon color
    edge_array = np.array(edge_img)
    outline_array = np.zeros((height, width, 4), dtype=np.uint8)
    
    # Set color where edges exist
    edge_mask_bool = edge_array > 128
    outline_array[edge_mask_bool, 0] = color[0]
    outline_array[edge_mask_bool, 1] = color[1]
    outline_array[edge_mask_bool, 2] = color[2]
    outline_array[edge_mask_bool, 3] = int(intensity * 255)
    
    outline_overlay = Image.fromarray(outline_array, mode='RGBA')
    
    # Create glow effect by blurring the outline
    glow_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_array = np.zeros((height, width, 4), dtype=np.uint8)
    
    # More intense color for glow base
    glow_array[edge_mask_bool, 0] = color[0]
    glow_array[edge_mask_bool, 1] = color[1]
    glow_array[edge_mask_bool, 2] = color[2]
    glow_array[edge_mask_bool, 3] = int(intensity * 180)
    
    glow_overlay = Image.fromarray(glow_array, mode='RGBA')
    
    # Apply multiple blur passes for soft glow
    glow_overlay = glow_overlay.filter(ImageFilter.GaussianBlur(radius=glow_radius))
    glow_overlay = glow_overlay.filter(ImageFilter.GaussianBlur(radius=glow_radius / 2))
    
    # Composite: glow first (underneath), then sharp outline on top
    result = Image.alpha_composite(image, glow_overlay)
    return Image.alpha_composite(result, outline_overlay)


def apply_echo_trail(
    image: Image.Image,
    echo_frames: List[Image.Image],
    trail_count: int,
    decay: float,
    intensity: float,
    offset_x: float = 0,
    offset_y: float = 0
) -> Image.Image:
    """Apply echo/ghost trail effect with offset to create visible trailing.
    
    Each echo is offset progressively further based on age, creating
    a motion blur / speed lines effect even on static images.
    
    Args:
        offset_x, offset_y: Per-frame offset in pixels. Older echoes are
            offset by age * offset. If both are 0, uses a default diagonal offset.
    """
    if not echo_frames or intensity < 0.01:
        return image
    
    width, height = image.size
    
    # Default offset creates a subtle diagonal trailing effect
    # Scale offset based on image size for consistent appearance
    if offset_x == 0 and offset_y == 0:
        base_offset = max(width, height) * 0.008 * intensity  # ~0.8% of image per echo
        offset_x = base_offset
        offset_y = base_offset * 0.5  # Slightly more horizontal than vertical
    
    # Start with transparent canvas to composite echoes underneath
    result = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    # Draw older echoes first (furthest back), working toward newer
    frames_to_use = echo_frames[-trail_count:]
    
    # Process from oldest to newest (oldest drawn first, underneath)
    for i, old_frame in enumerate(frames_to_use):
        # Age: oldest frame has highest age
        age = len(frames_to_use) - i
        alpha = intensity * (decay ** age)
        
        if alpha < 0.03:
            continue
        
        # Calculate offset for this echo (older = further offset)
        echo_offset_x = int(offset_x * age)
        echo_offset_y = int(offset_y * age)
        
        # Create offset version of the frame
        offset_frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        
        # Paste the old frame with offset (crop to stay within bounds)
        paste_x = -echo_offset_x
        paste_y = -echo_offset_y
        offset_frame.paste(old_frame, (paste_x, paste_y))
        
        # Apply alpha to the offset frame
        # We need to modify just the alpha channel, preserving RGB
        r, g, b, a = offset_frame.split()
        # Multiply existing alpha by our decay alpha
        a = a.point(lambda x: int(x * alpha))
        offset_frame = Image.merge("RGBA", (r, g, b, a))
        
        # Composite onto result
        result = Image.alpha_composite(result, offset_frame)
    
    # Finally composite the current image on top
    result = Image.alpha_composite(result, image)
    
    return result


def apply_energy_trails(
    image: Image.Image,
    params: Dict[str, Any],
    width: int, height: int
) -> Image.Image:
    """Draw energy trails orbiting the element in an ellipse matching subject bounds."""
    if not params:
        return image
    
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    count = params.get("count", 8)
    colors = params.get("colors", [(255, 200, 100)])
    trail_width = params.get("width", 2)
    speed = params.get("speed", 1.0)
    time = params.get("time", 0)
    intensity = params.get("intensity", 0.5)
    
    # Get bounds and calculate elliptical orbit
    bounds_x = params.get("bounds_x", 0.25)
    bounds_y = params.get("bounds_y", 0.25)
    bounds_w = params.get("bounds_w", 0.5)
    bounds_h = params.get("bounds_h", 0.5)
    
    # Center of the ellipse
    center_x = (bounds_x + bounds_w / 2) * width
    center_y = (bounds_y + bounds_h / 2) * height
    
    # Orbit radii based on subject size (slightly larger than bounds)
    orbit_radius_x = (bounds_w / 2) * width * 1.3
    orbit_radius_y = (bounds_h / 2) * height * 1.3
    
    for i in range(count):
        base_angle = (i / count) * 2 * math.pi
        angle = base_angle + time * speed * 2 * math.pi
        
        # Calculate trail positions
        color = colors[i % len(colors)]
        alpha = int(intensity * 200)
        
        # Draw trail as arc following ellipse
        trail_length = 0.3  # Radians
        points = []
        for t in np.linspace(0, trail_length, 20):
            a = angle - t
            # Fade radius as trail extends
            fade_factor = (1 - t / trail_length * 0.3)
            rx = orbit_radius_x * fade_factor
            ry = orbit_radius_y * fade_factor
            px = center_x + math.cos(a) * rx
            py = center_y + math.sin(a) * ry
            points.append((px, py))
        
        # Draw with fading alpha
        for j in range(len(points) - 1):
            fade = 1 - j / len(points)
            trail_alpha = int(alpha * fade)
            trail_color = (*color, trail_alpha)
            draw.line([points[j], points[j + 1]], fill=trail_color, width=int(trail_width))
    
    # Blur for glow effect
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=trail_width))
    
    return Image.alpha_composite(image, overlay)


def apply_light_flares(
    image: Image.Image,
    points: List[Tuple[float, float]],
    intensity: float,
    size: float,
    colors: List[Tuple[int, int, int]],
    width: int, height: int
) -> Image.Image:
    """Apply lens flare effect at specified points."""
    if intensity < 0.01 or not points:
        return image
    
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    for i, (px, py) in enumerate(points):
        x = int(px * width)
        y = int(py * height)
        color = colors[i % len(colors)]
        
        # Draw main flare
        for r in range(int(size), 0, -5):
            alpha = int(intensity * 150 * (r / size))
            flare_color = (*color, alpha)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=flare_color)
        
        # Draw horizontal streak
        streak_length = int(size * 1.5)
        for offset in range(-streak_length, streak_length, 2):
            dist = abs(offset) / streak_length
            alpha = int(intensity * 100 * (1 - dist))
            streak_color = (*color, alpha)
            draw.ellipse([x + offset - 3, y - 3, x + offset + 3, y + 3], fill=streak_color)
    
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=size / 5))
    
    return Image.alpha_composite(image, overlay)


def apply_glitch(
    image: Image.Image,
    intensity: float,
    chromatic: float,
    rgb_split: float,
    scan_lines: bool,
    scan_opacity: float,
    slice_effect: bool
) -> Image.Image:
    """Apply glitch effects."""
    if intensity < 0.05:
        return image
    
    result = image.copy()
    width, height = result.size
    
    # RGB split / chromatic aberration
    if chromatic > 0.5 or rgb_split > 0.5:
        offset = int(max(chromatic, rgb_split) * intensity)
        if offset > 0:
            r, g, b = result.convert("RGB").split()
            
            r_shifted = Image.new("L", (width, height), 0)
            r_shifted.paste(r, (-offset, 0))
            
            b_shifted = Image.new("L", (width, height), 0)
            b_shifted.paste(b, (offset, 0))
            
            result = Image.merge("RGB", (r_shifted, g, b_shifted))
            result = result.convert("RGBA")
    
    # Scan lines
    if scan_lines and scan_opacity > 0.01:
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        alpha = int(scan_opacity * 255)
        for y in range(0, height, 4):
            draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha), width=1)
        
        result = Image.alpha_composite(result, overlay)
    
    # Slice displacement
    if slice_effect and intensity > 0.3:
        num_slices = int(3 + intensity * 5)
        for _ in range(num_slices):
            y = random.randint(0, height - 20)
            slice_height = random.randint(5, 20)
            displacement = random.randint(-int(20 * intensity), int(20 * intensity))
            
            if displacement != 0:
                slice_region = result.crop((0, y, width, y + slice_height))
                result.paste(slice_region, (displacement, y))
    
    return result


def apply_film_grain(
    image: Image.Image,
    intensity: float,
    grain_size: float
) -> Image.Image:
    """Apply film grain texture."""
    if intensity < 0.01:
        return image
    
    width, height = image.size
    
    # Create noise
    noise = np.random.normal(0, intensity * 50, (height, width, 3)).astype(np.int16)
    
    # Apply to image
    img_array = np.array(image.convert("RGB")).astype(np.int16)
    result = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    
    result_img = Image.fromarray(result, mode="RGB").convert("RGBA")
    
    # Preserve alpha
    if image.mode == "RGBA":
        result_img.putalpha(image.split()[3])
    
    return result_img


def apply_strobe_flash(
    image: Image.Image,
    intensity: float,
    color: Tuple[int, int, int]
) -> Image.Image:
    """Apply strobe flash effect with radial falloff - bright center, fading edges."""
    if intensity < 0.01:
        return image
    
    width, height = image.size
    cx, cy = width // 2, height // 2
    
    # Create coordinate grids for radial falloff
    y_coords, x_coords = np.mgrid[0:height, 0:width].astype(np.float32)
    
    # Calculate distance from center
    max_dist = math.sqrt(cx * cx + cy * cy)
    dist = np.sqrt((x_coords - cx) ** 2 + (y_coords - cy) ** 2)
    normalized_dist = dist / max_dist
    
    # Create radial falloff - bright in center, fades toward edges
    # Using smooth falloff curve
    falloff = 1 - (normalized_dist ** 0.7)
    falloff = np.clip(falloff, 0, 1)
    
    # Reduce max intensity significantly - 80 alpha max instead of 200
    # This creates a bright highlight rather than whiteout
    max_alpha = intensity * 80
    alpha_array = (falloff * max_alpha).astype(np.uint8)
    
    # Create the flash overlay with gradient alpha
    flash_rgb = Image.new("RGB", (width, height), color)
    flash_alpha = Image.fromarray(alpha_array, mode="L")
    flash = flash_rgb.copy()
    flash.putalpha(flash_alpha)
    
    return Image.alpha_composite(image, flash)


def apply_vignette(
    image: Image.Image,
    strength: float,
    width: int, height: int
) -> Image.Image:
    """Apply vignette effect (darkened edges) using vectorized NumPy operations."""
    if strength < 0.01:
        return image
    
    cx, cy = width // 2, height // 2
    max_dist = math.sqrt(cx * cx + cy * cy)
    
    # Create coordinate grids using NumPy
    y_coords, x_coords = np.mgrid[0:height, 0:width].astype(np.float32)
    
    # Calculate normalized distance from center (vectorized)
    dist = np.sqrt((x_coords - cx) ** 2 + (y_coords - cy) ** 2)
    normalized_dist = dist / max_dist
    
    # Calculate vignette values (vectorized)
    vignette = 1 - (normalized_dist ** 2) * strength
    vignette = np.clip(vignette, 0, 1)
    
    # Convert to mask image
    mask_array = (vignette * 255).astype(np.uint8)
    mask = Image.fromarray(mask_array, mode="L")
    
    # Apply vignette
    darkened = image.copy()
    enhancer = ImageEnhance.Brightness(darkened)
    darkened = enhancer.enhance(0.3)
    
    return Image.composite(image, darkened, mask)
