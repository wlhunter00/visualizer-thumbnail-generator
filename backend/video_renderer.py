"""
Video Renderer Module
Generates beat-reactive videos with 13 customizable effects using layer compositing.
"""

import os
import math
import random
import subprocess
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, List, Tuple, Dict, Any

from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
import numpy as np

from effect_engine import EffectParameters, get_effect_value_at_time
from image_analysis import preprocess_particle_sprite


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

PREVIEW_REFERENCE_WIDTH = 540

_nvenc_available_cache: Optional[bool] = None
_NVIDIA_DEVICE = "/dev/nvidia0"
_LIBCUDA_NAMES = ("libcuda.so.1", "nvcuda.dll")


def _cuda_present() -> bool:
    """True if an NVIDIA GPU / CUDA driver is actually usable.

    FFmpeg may list h264_nvenc even when libcuda.so.1 and /dev/nvidia0
    are missing (CPU-only Linux / Cursor boxes). Compiled-in encoder
    names are not enough.
    """
    if os.path.exists(_NVIDIA_DEVICE):
        return True
    try:
        import ctypes
        for name in _LIBCUDA_NAMES:
            try:
                ctypes.CDLL(name)
                return True
            except OSError:
                continue
    except Exception:
        return False
    return False


def _nvenc_available() -> bool:
    """True only if FFmpeg has h264_nvenc *and* CUDA is actually present."""
    global _nvenc_available_cache
    if _nvenc_available_cache is not None:
        return _nvenc_available_cache
    if not _cuda_present():
        _nvenc_available_cache = False
        return False
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        _nvenc_available_cache = (
            result.returncode == 0 and "h264_nvenc" in result.stdout
        )
    except Exception:
        _nvenc_available_cache = False
    return _nvenc_available_cache


def _ffmpeg_video_encode_args(quality: str, preview: bool) -> Tuple[List[str], str]:
    """Return FFmpeg video encode flags and a label for logging."""
    if preview:
        return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28"], "libx264"

    crf = {"low": 28, "medium": 23, "high": 18}.get(quality, 23)
    if _nvenc_available():
        return [
            "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-rc", "vbr",
            "-cq", str(crf),
            "-b:v", "0",
        ], "h264_nvenc"

    return [
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", str(crf),
    ], "libx264"


def preview_scale(width: int) -> float:
    """Scale preview-tuned pixel values to the current render width."""
    return width / PREVIEW_REFERENCE_WIDTH


@dataclass
class RenderSettings:
    aspect_ratio: AspectRatio = AspectRatio.VERTICAL
    fps: int = 30
    quality: str = "medium"
    duration: float = 30.0
    preview: bool = False
    resolution_scale: float = 1.0  # Multiplier for output resolution


def resolve_render_dimensions(
    render_settings: RenderSettings,
) -> Tuple[int, int, Image.Resampling]:
    """Return width, height, and resampling filter for the given render settings."""
    if render_settings.preview:
        width, height = PREVIEW_DIMENSIONS[render_settings.aspect_ratio]
        resampling = Image.Resampling.BILINEAR
    else:
        base_width, base_height = ASPECT_DIMENSIONS[render_settings.aspect_ratio]
        scale = render_settings.resolution_scale
        width = int(base_width * scale)
        height = int(base_height * scale)
        width = width + (width % 2)
        height = height + (height % 2)
        resampling = Image.Resampling.LANCZOS
    return width, height, resampling


class RawFramePipeEncoder:
    """
    Stream RGB frames into FFmpeg over stdin (no JPEG temp files).

    Encoding overlaps with frame rendering. Call write_frame() for each frame,
    then finish() after the last frame.
    """

    def __init__(
        self,
        width: int,
        height: int,
        fps: int,
        audio_path: str,
        audio_start: float,
        duration: float,
        output_path: str,
        render_settings: RenderSettings,
    ):
        video_encode_args, self.encoder_name = _ffmpeg_video_encode_args(
            render_settings.quality, render_settings.preview
        )
        self._frame_bytes = width * height * 3
        self._start = time.perf_counter()
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{width}x{height}",
            "-framerate", str(fps),
            "-i", "pipe:0",
            "-ss", str(audio_start),
            "-t", str(duration),
            "-i", audio_path,
            *video_encode_args,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path,
        ]
        self._proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self._stderr_chunks: List[bytes] = []
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr, daemon=True
        )
        self._stderr_thread.start()

    def _drain_stderr(self) -> None:
        stderr = self._proc.stderr
        if stderr is None:
            return
        while True:
            chunk = stderr.read(4096)
            if not chunk:
                break
            self._stderr_chunks.append(chunk)

    def write_frame(self, frame: Image.Image) -> None:
        """Write one RGB frame to the encoder pipe."""
        if self._proc.stdin is None:
            raise RuntimeError("FFmpeg stdin is not available")
        rgb = frame.convert("RGB")
        data = rgb.tobytes()
        if len(data) != self._frame_bytes:
            raise RuntimeError(
                f"Frame size mismatch: got {len(data)} bytes, "
                f"expected {self._frame_bytes}"
            )
        try:
            self._proc.stdin.write(data)
        except BrokenPipeError as exc:
            self._stderr_thread.join(timeout=5)
            err = b"".join(self._stderr_chunks).decode("utf-8", errors="replace")
            raise RuntimeError(
                f"FFmpeg pipe broke while writing frames: {err or exc}"
            ) from exc

    def finish(self) -> Tuple[str, float]:
        """Close the pipe and wait for FFmpeg. Returns (encoder_name, elapsed_s)."""
        if self._proc.stdin is not None:
            try:
                self._proc.stdin.close()
            except BrokenPipeError:
                pass
        returncode = self._proc.wait()
        self._stderr_thread.join(timeout=5)
        elapsed = time.perf_counter() - self._start
        if returncode != 0:
            err = b"".join(self._stderr_chunks).decode("utf-8", errors="replace")
            raise RuntimeError(
                f"FFmpeg failed (exit code {returncode}): {err or 'Unknown FFmpeg error'}"
            )
        return self.encoder_name, elapsed

    def abort(self) -> None:
        """Best-effort cleanup if rendering fails mid-stream."""
        try:
            if self._proc.stdin is not None and not self._proc.stdin.closed:
                self._proc.stdin.close()
        except Exception:
            pass
        if self._proc.poll() is None:
            self._proc.kill()
            self._proc.wait(timeout=10)


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

    def __init__(self, particle_sprite: Optional[Image.Image] = None):
        self.particles: List[Particle] = []
        self.particle_sprite = particle_sprite
        self._sprite_cache: Dict[int, Image.Image] = {}

    def _resized_sprite(self, diameter: int) -> Image.Image:
        """Return a cached BILINEAR resize of the particle sprite."""
        cached = self._sprite_cache.get(diameter)
        if cached is not None:
            return cached
        assert self.particle_sprite is not None
        sprite = self.particle_sprite.resize(
            (diameter, diameter), Image.Resampling.BILINEAR,
        )
        if sprite.mode != "RGBA":
            sprite = sprite.convert("RGBA")
        self._sprite_cache[diameter] = sprite
        return sprite

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
        width: int, height: int,
        strength: float = 1.0,
    ):
        """Spawn particles from the perimeter of the subject's elliptical bounds."""
        scale = preview_scale(width)
        scaled_speed = speed * scale
        scaled_size_range = (size_range[0] * scale, size_range[1] * scale)
        spawn_count = max(1, int(count * max(strength, 0.1)))
        # Calculate center and radii in pixels
        center_x = (bounds_x + bounds_w / 2) * width
        center_y = (bounds_y + bounds_h / 2) * height
        radius_x = (bounds_w / 2) * width * 1.1  # Slightly outside bounds
        radius_y = (bounds_h / 2) * height * 1.1
        
        for _ in range(spawn_count):
            # Random angle around the ellipse perimeter
            angle = random.random() * 2 * math.pi
            
            # Spawn position on ellipse perimeter
            spawn_x = center_x + math.cos(angle) * radius_x
            spawn_y = center_y + math.sin(angle) * radius_y
            
            # Velocity radiates outward from center
            velocity = scaled_speed * (0.5 + random.random() * 0.5)
            
            self.particles.append(Particle(
                x=spawn_x,
                y=spawn_y,
                vx=math.cos(angle) * velocity,
                vy=math.sin(angle) * velocity,
                size=random.uniform(scaled_size_range[0], scaled_size_range[1]),
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

        for p in self.particles:
            age = time - p.birth_time
            progress = age / p.lifetime
            alpha = int(p.alpha * (1 - progress) * 255)
            if alpha <= 0:
                continue

            size = p.size * (1 - progress * 0.5)
            x, y = int(p.x), int(p.y)
            r = max(1, int(size / 2))
            if r <= 0:
                continue

            if self.particle_sprite is not None:
                sprite = self._resized_sprite(r * 2)
                alpha_mask = sprite.split()[3].point(lambda a, al=alpha: int(a * al / 255))
                if alpha_mask.getextrema()[1] < 8:
                    draw = ImageDraw.Draw(overlay)
                    draw.ellipse([x - r, y - r, x + r, y + r], fill=(*p.color, alpha))
                    continue
                tinted = Image.new("RGBA", sprite.size, (*p.color, alpha))
                tinted.putalpha(alpha_mask)
                overlay.paste(tinted, (x - r, y - r), alpha_mask)
            else:
                draw = ImageDraw.Draw(overlay)
                draw.ellipse([x - r, y - r, x + r, y + r], fill=(*p.color, alpha))

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
    width, height, resampling = resolve_render_dimensions(render_settings)
    
    fps = render_settings.fps
    duration = render_settings.duration
    total_frames = int(duration * fps)
    
    # Load and prepare base image
    base_image = Image.open(image_path).convert("RGBA")
    base_image = fit_image_to_frame(base_image, width, height, resampling)
    
    frame_state = prepare_frame_render_state(
        base_image, effect_params, width, height, resampling,
        custom_particle_sprite=custom_particle_sprite,
    )

    burst = effect_params.particle_burst
    sprite = frame_state.particle_system.particle_sprite
    sprite_info = (
        f"loaded({sprite.width}x{sprite.height})"
        if sprite is not None
        else ("missing" if custom_particle_sprite else "none")
    )
    print(
        f"[export] particle_burst enabled={burst.enabled} "
        f"triggers={len(burst.triggers) if burst.enabled else 0} sprite={sprite_info}"
    )

    render_start = time.perf_counter()
    logged_particle_frame = False
    encoder = RawFramePipeEncoder(
        width=width,
        height=height,
        fps=fps,
        audio_path=audio_path,
        audio_start=audio_start,
        duration=duration,
        output_path=output_path,
        render_settings=render_settings,
    )

    try:
        for frame_num in range(total_frames):
            time_sec = frame_num / fps
            dt = 1.0 / fps

            if frame_num % 100 == 0:
                elapsed = time.perf_counter() - render_start
                print(
                    f"[render_video] frame {frame_num}/{total_frames} "
                    f"({elapsed:.0f}s elapsed)"
                )

            frame = render_single_frame_cpu(
                frame_state, effect_params, time_sec, dt,
            )

            if not logged_particle_frame and frame_state.particle_system.particles:
                print(
                    f"[export] frame {frame_num}: "
                    f"particles={len(frame_state.particle_system.particles)}"
                )
                logged_particle_frame = True

            encoder.write_frame(frame)

            if progress_callback:
                progress_callback((frame_num + 1) / total_frames * 0.9)

        if progress_callback:
            progress_callback(0.95)

        encoder_name, _encode_elapsed = encoder.finish()
    except Exception:
        encoder.abort()
        raise

    total_elapsed = time.perf_counter() - render_start
    print(
        f"[render_video] renderer=cpu {total_frames} frames @ {width}x{height} "
        f"encoder={encoder_name}: "
        f"total={total_elapsed:.1f}s (streamed encode)"
    )

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
    focus_radius: float,
    width: int, height: int
) -> Image.Image:
    """Dim and blur the background outside the subject bounds."""
    if dim_amount < 0.01 and blur_amount < 0.1:
        return image
    
    # Create darkened/blurred version
    bg = image.copy()
    
    if blur_amount > 0.1:
        scaled_blur = blur_amount * preview_scale(width)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=scaled_blur))
    
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
    
    min_dim = min(w, h)
    max_dim = max(w, h)
    padding = int(min_dim * (0.05 + focus_radius * 0.45))
    expand = int(max_dim * focus_radius * 0.3)
    draw.ellipse(
        [x - padding - expand, y - padding - expand, x + w + padding + expand, y + h + padding + expand],
        fill=255,
    )
    
    # Blur the mask for soft edges
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(1, int(padding * (0.8 + focus_radius * 0.4)))))
    
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
    
    scale = preview_scale(width)
    ripple_radius = ripple.get("radius", 100) * scale
    amplitude = ripple.get("amplitude", 10) * intensity * scale
    wavelength = ripple.get("wavelength", 50) * scale
    
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
    
    scaled_radius = radius * preview_scale(width)

    # Create glow layer
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    
    cx = int(bounds.get("center_x", 0.5) * width)
    cy = int(bounds.get("center_y", 0.5) * height)
    bw = int(bounds.get("w", 0.5) * width)
    bh = int(bounds.get("h", 0.5) * height)
    
    # Draw multiple ellipses for glow
    step = max(3, int(5 * preview_scale(width)))
    for i in range(int(scaled_radius), 0, -step):
        alpha = int(intensity * 100 * (i / scaled_radius))
        glow_color = (*color, min(255, alpha))
        
        rx = bw // 2 + i
        ry = bh // 2 + i
        
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=glow_color)
    
    # Blur the glow
    glow = glow.filter(ImageFilter.GaussianBlur(radius=scaled_radius / 3))
    
    return Image.alpha_composite(image, glow)


def apply_neon_outline(
    image: Image.Image,
    bounds: Dict[str, float],
    intensity: float,
    color: Tuple[int, int, int],
    width: float,
    glow_radius: float,
    frame_width: int,
    frame_height: int,
) -> Image.Image:
    """Draw a neon stroke around the subject bounds with blurred glow."""
    if intensity < 0.01:
        return image

    scale = preview_scale(frame_width)
    x = int(bounds.get("x", 0.25) * frame_width)
    y = int(bounds.get("y", 0.25) * frame_height)
    w = int(bounds.get("w", 0.5) * frame_width)
    h = int(bounds.get("h", 0.5) * frame_height)
    line_width = max(1, int(width * scale))
    glow = glow_radius * scale
    alpha = int(intensity * 255)

    overlay = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.ellipse(
        [x, y, x + w, y + h],
        outline=(*color, alpha),
        width=line_width,
    )
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=max(1, glow / 2)))
    return Image.alpha_composite(image, overlay)


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
    trail_width = params.get("width", 2) * preview_scale(width)
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
    
    # Orbit radii based on subject size (matches preview: 1.2x bounds)
    orbit_radius_x = (bounds_w / 2) * width * 1.2
    orbit_radius_y = (bounds_h / 2) * height * 1.2
    
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
    
    scaled_size = size * preview_scale(width)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    for i, (px, py) in enumerate(points):
        x = int(px * width)
        y = int(py * height)
        color = colors[i % len(colors)]
        
        # Draw main flare
        step = max(3, int(5 * preview_scale(width)))
        for r in range(int(scaled_size * intensity), 0, -step):
            flare_radius = scaled_size * intensity
            alpha = int(intensity * 150 * (r / flare_radius)) if flare_radius > 0 else 0
            flare_color = (*color, alpha)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=flare_color)
        
        # Draw horizontal streak
        streak_length = int(scaled_size * intensity * 1.5)
        dot_radius = max(2, int(3 * preview_scale(width)))
        for offset in range(-streak_length, streak_length, 2):
            dist = abs(offset) / max(streak_length, 1)
            alpha = int(intensity * 100 * (1 - dist))
            streak_color = (*color, alpha)
            draw.ellipse(
                [x + offset - dot_radius, y - dot_radius, x + offset + dot_radius, y + dot_radius],
                fill=streak_color,
            )
    
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=max(1, scaled_size / 5)))
    
    return Image.alpha_composite(image, overlay)


def _seeded_slice_offset(seed: float, band: int, magnitude: float) -> float:
    x = math.sin(seed * 0.001 + band * 12.9898) * 43758.5453
    frac = x - math.floor(x)
    return (frac - 0.5) * magnitude * 4


def apply_chromatic_glitch(
    image: Image.Image,
    chromatic: float,
    rgb_split: float,
    scan_lines: bool,
    scan_opacity: float,
    width: int,
    height: int,
) -> Image.Image:
    """RGB channel separation on composited frame (matches preview glitch.ts)."""
    scale = preview_scale(width)
    split_px = max(chromatic, rgb_split) * scale
    offset = max(int(round(split_px)), int(round(2 * scale)))
    if offset <= 0:
        return image

    result = image.copy().convert("RGBA")
    r, g, b = result.convert("RGB").split()
    alpha = result.split()[3]

    r_shifted = Image.new("L", (width, height), 0)
    r_shifted.paste(r, (-offset, 0))
    b_shifted = Image.new("L", (width, height), 0)
    b_shifted.paste(b, (offset, 0))

    merged = Image.merge("RGB", (r_shifted, g, b_shifted)).convert("RGBA")
    merged.putalpha(alpha)
    result = merged

    if scan_lines and scan_opacity > 0.01:
        scan_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(scan_overlay)
        alpha_val = int(scan_opacity * 255)
        line_step = max(2, int(round(4 * scale)))
        line_height = max(1, int(round(2 * scale)))
        for y in range(0, height, line_step):
            draw.rectangle([(0, y), (width, y + line_height - 1)], fill=(0, 0, 0, alpha_val))
        result = Image.alpha_composite(result, scan_overlay)

    return result


def apply_slice_glitch(
    image: Image.Image,
    offset_px: float,
    width: int,
    height: int,
    seed: float,
) -> Image.Image:
    """Horizontal band displacement on alternating slices."""
    scale = preview_scale(width)
    split_px = offset_px * scale
    if split_px <= 0:
        return image

    result = image.copy()
    slice_h = max(1, height // 8)
    for i in range(0, 8, 2):
        y0 = i * slice_h
        y1 = min((i + 1) * slice_h, height)
        displacement = int(round(_seeded_slice_offset(seed, i, split_px)))
        if displacement != 0:
            slice_region = result.crop((0, y0, width, y1))
            result.paste(slice_region, (displacement, y0))

    return result


def apply_film_grain(
    image: Image.Image,
    intensity: float,
    grain_size: float
) -> Image.Image:
    """Apply film grain texture with configurable grain size."""
    if intensity < 0.01:
        return image

    width, height = image.size
    scale = preview_scale(width)
    block = max(1, int(grain_size * scale))
    small_w = max(1, width // block)
    small_h = max(1, height // block)
    noise_small = np.random.randint(0, 256, (small_h, small_w), dtype=np.uint8)
    noise_img = Image.fromarray(noise_small, mode="L").resize(
        (width, height), Image.Resampling.NEAREST,
    )
    noise = np.array(noise_img)
    noise_rgb = np.stack([noise, noise, noise], axis=-1)
    alpha = int(intensity * 0.25 * 255)
    noise_rgba = np.dstack([noise_rgb, np.full((height, width), alpha, dtype=np.uint8)])
    overlay = Image.fromarray(noise_rgba, mode="RGBA")
    return Image.alpha_composite(image, overlay)


def apply_strobe_flash(
    image: Image.Image,
    intensity: float,
    color: Tuple[int, int, int]
) -> Image.Image:
    """Apply full-frame strobe flash (matches preview drawStrobe)."""
    if intensity < 0.01:
        return image
    
    width, height = image.size
    alpha = int(intensity * 0.7 * 255)
    flash = Image.new("RGBA", (width, height), (*color, alpha))
    return Image.alpha_composite(image, flash)


def build_vignette_dist_sq(width: int, height: int) -> np.ndarray:
    """Precompute squared normalized distance from center for vignette masking."""
    cx, cy = width // 2, height // 2
    max_dist = math.sqrt(cx * cx + cy * cy)
    y_coords, x_coords = np.mgrid[0:height, 0:width].astype(np.float32)
    dist = np.sqrt((x_coords - cx) ** 2 + (y_coords - cy) ** 2)
    return (dist / max_dist) ** 2


def apply_vignette(
    image: Image.Image,
    strength: float,
    dist_sq: np.ndarray,
) -> Image.Image:
    """Apply vignette effect (darkened edges) using a precomputed distance field."""
    if strength < 0.01:
        return image

    vignette = 1 - dist_sq * strength
    vignette = np.clip(vignette, 0, 1)

    mask_array = (vignette * 255).astype(np.uint8)
    mask = Image.fromarray(mask_array, mode="L")

    darkened = image.copy()
    enhancer = ImageEnhance.Brightness(darkened)
    darkened = enhancer.enhance(0.3)

    return Image.composite(image, darkened, mask)


@dataclass
class FrameRenderState:
    """Mutable per-export state shared across frames."""
    base_image: Image.Image
    background_dim_base: Image.Image
    bg_dim_enabled: bool
    vignette_dist_sq: np.ndarray
    bounds_dict: Dict[str, float]
    width: int
    height: int
    resampling: Image.Resampling
    particle_system: ParticleSystem
    previous_bursts: set


def _load_particle_sprite(path: Optional[str]) -> Optional[Image.Image]:
    if not path or not os.path.exists(path):
        return None
    try:
        return preprocess_particle_sprite(Image.open(path))
    except Exception:
        return None


def prepare_frame_render_state(
    base_image: Image.Image,
    effect_params: EffectParameters,
    width: int,
    height: int,
    resampling: Image.Resampling,
    custom_particle_sprite: Optional[str] = None,
) -> FrameRenderState:
    """Build per-export frame state (precomputed masks, particle system, etc.)."""
    bounds_dict = {
        "x": effect_params.subject_bounds.x,
        "y": effect_params.subject_bounds.y,
        "w": effect_params.subject_bounds.w,
        "h": effect_params.subject_bounds.h,
        "center_x": effect_params.subject_bounds.center_x,
        "center_y": effect_params.subject_bounds.center_y,
    }
    background_dim_base = base_image
    bg_dim = effect_params.background_dim
    if bg_dim.enabled:
        background_dim_base = apply_background_dim(
            base_image,
            bounds_dict,
            bg_dim.dim_amount,
            bg_dim.blur_amount,
            bg_dim.focus_radius,
            width,
            height,
        )
    return FrameRenderState(
        base_image=base_image,
        background_dim_base=background_dim_base,
        bg_dim_enabled=bg_dim.enabled,
        vignette_dist_sq=build_vignette_dist_sq(width, height),
        bounds_dict=bounds_dict,
        width=width,
        height=height,
        resampling=resampling,
        particle_system=ParticleSystem(_load_particle_sprite(custom_particle_sprite)),
        previous_bursts=set(),
    )


def render_single_frame_cpu(
    state: FrameRenderState,
    effect_params: EffectParameters,
    time_sec: float,
    dt: float,
    effects: Optional[Dict[str, Any]] = None,
) -> Image.Image:
    """Render one composited frame on CPU (PIL). Used by CPU export and parity tests."""
    if effects is None:
        effects = get_effect_value_at_time(effect_params, time_sec)

    bounds = effects.get("subject_bounds", state.bounds_dict)
    width, height = state.width, state.height

    frame = (
        state.background_dim_base.copy()
        if state.bg_dim_enabled
        else state.base_image.copy()
    )

    ripples = effects.get("ripple_waves", [])
    if ripples:
        for ripple in ripples:
            frame = apply_ripple_wave(
                frame, ripple, width, height,
                effects.get("ripple_intensity", 0.5),
            )

    scale = effects.get("element_scale", 1.0)
    if abs(scale - 1.0) > 0.001:
        frame = apply_element_scale(
            frame, bounds, scale, width, height, state.resampling,
        )

    glow_intensity = effects.get("element_glow_intensity", 0)
    if glow_intensity > 0.01:
        frame = apply_element_glow(
            frame, bounds,
            glow_intensity,
            effects.get("element_glow_radius", 50),
            effects.get("element_glow_color", (255, 200, 100)),
            width, height,
        )

    neon_intensity = effects.get("neon_outline_intensity", 0)
    if neon_intensity > 0.01:
        frame = apply_neon_outline(
            frame, bounds,
            neon_intensity,
            effects.get("neon_outline_color", (0, 255, 255)),
            effects.get("neon_outline_width", 3),
            effects.get("neon_outline_glow", 15),
            width, height,
        )

    bursts = effects.get("particle_bursts", [])
    burst_params = effects.get("particle_burst_params", {})
    for burst in bursts:
        trigger_time = burst.get("trigger_time")
        burst_id = (
            trigger_time,
            burst.get("bounds_x", 0.25),
            burst.get("bounds_y", 0.25),
        )
        if burst_id in state.previous_bursts:
            continue
        state.previous_bursts.add(burst_id)
        state.particle_system.spawn_burst_from_bounds(
            bounds_x=burst.get("bounds_x", 0.25),
            bounds_y=burst.get("bounds_y", 0.25),
            bounds_w=burst.get("bounds_w", 0.5),
            bounds_h=burst.get("bounds_h", 0.5),
            count=burst_params.get("count", 50),
            colors=burst_params.get(
                "colors",
                [(255, 255, 255), (255, 220, 180), (200, 220, 255)],
            ),
            size_range=burst_params.get("size_range", (3, 12)),
            speed=burst_params.get("speed", 200),
            lifetime=burst_params.get("lifetime", 1.0),
            time=time_sec,
            width=width,
            height=height,
            strength=burst.get("strength", 1.0),
        )

    state.particle_system.update(time_sec, dt)
    frame = state.particle_system.draw(frame, time_sec)

    if effects.get("energy_trails_enabled", False):
        frame = apply_energy_trails(
            frame,
            effects.get("energy_trails_params", {}),
            width, height,
        )

    flare_intensity = effects.get("light_flares_intensity", 0)
    if flare_intensity > 0.01:
        frame = apply_light_flares(
            frame,
            effects.get("light_flares_points", []),
            flare_intensity,
            effects.get("light_flares_size", 100),
            effects.get("light_flares_colors", [(255, 255, 200)]),
            width, height,
        )

    vignette_strength = effects.get("vignette_strength", 0)
    if vignette_strength > 0.01:
        frame = apply_vignette(frame, vignette_strength, state.vignette_dist_sq)

    if effects.get("film_grain_enabled", False):
        frame = apply_film_grain(
            frame,
            effects.get("film_grain_intensity", 0.2),
            effects.get("film_grain_size", 1.5),
        )

    if effects.get("strobe_active", False):
        frame = apply_strobe_flash(
            frame,
            effects.get("strobe_intensity", 0.5),
            effects.get("strobe_color", (255, 255, 255)),
        )

    if effects.get("glitch_active", False):
        frame = apply_chromatic_glitch(
            frame,
            effects.get("glitch_chromatic", 0),
            effects.get("glitch_rgb_split", 0),
            effects.get("glitch_scan_lines", False),
            effects.get("glitch_scan_opacity", 0),
            width,
            height,
        )

    if effects.get("glitch_slice_active", False):
        frame = apply_slice_glitch(
            frame,
            effects.get("glitch_slice_offset", 0),
            width,
            height,
            effects.get("glitch_slice_seed", 0),
        )

    return frame
