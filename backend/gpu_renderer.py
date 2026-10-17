"""
GPU-accelerated video renderer using PyTorch CUDA.
Optional dependency: pip install -r requirements-gpu.txt
"""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np
from PIL import Image

from effect_engine import EffectParameters, get_effect_value_at_time
from video_renderer import (
    FrameRenderState,
    RawFramePipeEncoder,
    RenderSettings,
    fit_image_to_frame,
    prepare_frame_render_state,
    preview_scale,
    resolve_render_dimensions,
    apply_energy_trails,
    apply_light_flares,
)

_torch = None
_F = None
_device_name_logged = False


def _import_torch():
    global _torch, _F
    if _torch is None:
        import torch
        import torch.nn.functional as F

        _torch = torch
        _F = F
    return _torch, _F


def cuda_available() -> bool:
    try:
        torch, _ = _import_torch()
        return torch.cuda.is_available()
    except ImportError:
        return False


def get_cuda_device_name() -> Optional[str]:
    if not cuda_available():
        return None
    torch, _ = _import_torch()
    return torch.cuda.get_device_name(0)


def resolve_renderer(mode: Optional[str] = None) -> str:
    """Pick cpu or gpu export path. EXPORT_RENDERER=auto|cpu|gpu (default auto)."""
    mode = (mode or os.getenv("EXPORT_RENDERER", "auto")).lower()
    if mode == "cpu":
        return "cpu"
    if mode == "gpu":
        if not cuda_available():
            raise RuntimeError(
                "EXPORT_RENDERER=gpu but CUDA is not available. "
                "Install CUDA PyTorch: pip install -r requirements-gpu.txt "
                "(use the CUDA wheel index from https://pytorch.org)"
            )
        return "gpu"
    if mode == "auto":
        if cuda_available():
            return "gpu"
        try:
            import torch  # noqa: F401
            reason = "torch installed but CUDA unavailable (CPU-only wheel?)"
        except ImportError:
            reason = "torch not installed (pip install -r requirements-gpu.txt)"
        print(f"[export] renderer=cpu ({reason})")
        return "cpu"
    raise ValueError(f"Invalid EXPORT_RENDERER={mode!r}; use auto, cpu, or gpu")


def _log_device_once() -> None:
    global _device_name_logged
    if not _device_name_logged and cuda_available():
        name = get_cuda_device_name() or "CUDA"
        print(f"[export] renderer=gpu device={name}")
        _device_name_logged = True


@dataclass
class GpuFrameRenderState:
    cpu_state: FrameRenderState
    device: Any
    base_tensor: Any
    background_dim_tensor: Any
    vignette_dist_sq: Any
    grid_y: Any
    grid_x: Any
    scale_mask: Any = None
    scale_mask_key: Optional[Tuple[int, int, int, int, int]] = None


def _pil_rgba_to_tensor(img: Image.Image, device: Any) -> Any:
    torch, _ = _import_torch()
    arr = np.asarray(img.convert("RGBA"), dtype=np.float32) / 255.0
    return torch.from_numpy(arr).to(device, non_blocking=True)


def _tensor_to_pil_rgba(tensor: Any) -> Image.Image:
    arr = (tensor.detach().float().clamp(0, 1).mul(255).byte().cpu().numpy())
    return Image.fromarray(arr, mode="RGBA")


def _tensor_to_rgb_bytes(tensor: Any) -> bytes:
    rgb = tensor[..., :3].detach().clamp(0, 1).mul(255).byte().contiguous()
    return rgb.cpu().numpy().tobytes()


def _alpha_composite(base: Any, overlay: Any) -> Any:
    torch, _ = _import_torch()
    oa = overlay[..., 3:4]
    ba = base[..., 3:4]
    out_a = oa + ba * (1 - oa)
    out_rgb = overlay[..., :3] * oa + base[..., :3] * ba * (1 - oa)
    out_rgb = out_rgb / torch.clamp(out_a, min=1e-6)
    return torch.cat([out_rgb, out_a], dim=-1)


def _gaussian_blur_rgba(tensor: Any, radius: float) -> Any:
    """Separable Gaussian blur (two 1D convs). Much faster than a 51x51 2D kernel on WDDM."""
    if radius < 0.1:
        return tensor
    torch, F = _import_torch()
    sigma = max(radius / 3.0, 0.1)
    ksize = max(3, int(radius * 2) | 1)
    ksize = min(ksize, 51)
    coords = torch.arange(ksize, device=tensor.device, dtype=tensor.dtype) - (ksize // 2)
    kernel_1d = torch.exp(-0.5 * (coords / sigma) ** 2)
    kernel_1d = kernel_1d / kernel_1d.sum()
    channels = tensor.shape[-1]
    chw = tensor.permute(2, 0, 1).unsqueeze(0)
    kx = kernel_1d.view(1, 1, 1, ksize).repeat(channels, 1, 1, 1)
    ky = kernel_1d.view(1, 1, ksize, 1).repeat(channels, 1, 1, 1)
    pad = ksize // 2
    chw = F.pad(chw, (pad, pad, 0, 0), mode="reflect")
    chw = F.conv2d(chw, kx, groups=channels)
    chw = F.pad(chw, (0, 0, pad, pad), mode="reflect")
    chw = F.conv2d(chw, ky, groups=channels)
    return chw.squeeze(0).permute(1, 2, 0)


def prepare_gpu_frame_render_state(
    base_image: Image.Image,
    effect_params: EffectParameters,
    width: int,
    height: int,
    resampling: Image.Resampling,
    custom_particle_sprite: Optional[str] = None,
) -> GpuFrameRenderState:
    cpu_state = prepare_frame_render_state(
        base_image, effect_params, width, height, resampling,
        custom_particle_sprite=custom_particle_sprite,
    )
    torch, _ = _import_torch()
    device = torch.device("cuda")
    y = torch.arange(height, device=device, dtype=torch.float32)
    x = torch.arange(width, device=device, dtype=torch.float32)
    grid_y, grid_x = torch.meshgrid(y, x, indexing="ij")
    return GpuFrameRenderState(
        cpu_state=cpu_state,
        device=device,
        base_tensor=_pil_rgba_to_tensor(cpu_state.base_image, device),
        background_dim_tensor=_pil_rgba_to_tensor(cpu_state.background_dim_base, device),
        vignette_dist_sq=torch.from_numpy(cpu_state.vignette_dist_sq).to(device),
        grid_y=grid_y,
        grid_x=grid_x,
    )


def _apply_ripple_gpu(
    frame: Any,
    ripple: Dict[str, Any],
    intensity: float,
    width: int,
    height: int,
    grid_y: Any,
    grid_x: Any,
    device: Any,
) -> Any:
    if intensity < 0.01:
        return frame
    torch, _ = _import_torch()
    bounds_x = ripple.get("bounds_x", 0.25)
    bounds_y = ripple.get("bounds_y", 0.25)
    bounds_w = ripple.get("bounds_w", 0.5)
    bounds_h = ripple.get("bounds_h", 0.5)
    center_x = (bounds_x + bounds_w / 2) * width
    center_y = (bounds_y + bounds_h / 2) * height
    radius_x = max((bounds_w / 2) * width, 1.0)
    radius_y = max((bounds_h / 2) * height, 1.0)
    scale = preview_scale(width)
    ripple_radius = ripple.get("radius", 100) * scale
    amplitude = ripple.get("amplitude", 10) * intensity * scale
    wavelength = max(ripple.get("wavelength", 50) * scale, 1e-3)
    if amplitude < 1:
        return frame

    dx = (grid_x - center_x) / radius_x
    dy = (grid_y - center_y) / radius_y
    ellipse_dist = torch.sqrt(dx * dx + dy * dy)
    avg_radius = (radius_x + radius_y) / 2
    dist_from_edge = (ellipse_dist - 1.0) * avg_radius
    angle = torch.atan2(grid_y - center_y, grid_x - center_x)
    affected = (dist_from_edge >= 0) & (torch.abs(dist_from_edge - ripple_radius) < wavelength * 2)
    wave = torch.sin((dist_from_edge - ripple_radius) * 2 * math.pi / wavelength)
    falloff = torch.exp(-((dist_from_edge - ripple_radius) / wavelength) ** 2)
    displacement = torch.where(affected, wave * amplitude * falloff, torch.zeros_like(wave))
    src_x = (grid_x + torch.cos(angle) * displacement).long().clamp(0, width - 1)
    src_y = (grid_y + torch.sin(angle) * displacement).long().clamp(0, height - 1)
    return frame[src_y, src_x]


def _scale_mask(state: GpuFrameRenderState, bx: int, by: int, bw: int, bh: int, feather: int) -> Any:
    torch, _ = _import_torch()
    key = (bx, by, bw, bh, feather)
    if state.scale_mask_key == key and state.scale_mask is not None:
        return state.scale_mask
    y = torch.arange(bh, device=state.device, dtype=torch.float32)
    x = torch.arange(bw, device=state.device, dtype=torch.float32)
    yy, xx = torch.meshgrid(y, x, indexing="ij")
    mask = ((xx / max(bw - 1, 1) - 0.5) * 2) ** 2 + ((yy / max(bh - 1, 1) - 0.5) * 2) ** 2 <= 1.0
    mask_f = mask.float().unsqueeze(-1)
    mask_f = _gaussian_blur_rgba(
        torch.cat([mask_f, mask_f, mask_f, torch.ones_like(mask_f)], dim=-1),
        float(feather),
    )[..., 3:4]
    state.scale_mask = mask_f
    state.scale_mask_key = key
    return mask_f


def _apply_element_scale_gpu(
    state: GpuFrameRenderState,
    frame: Any,
    bounds: Dict[str, float],
    scale: float,
    width: int,
    height: int,
) -> Any:
    if abs(scale - 1.0) < 0.001:
        return frame
    torch, F = _import_torch()
    bx = int(bounds.get("x", 0.25) * width)
    by = int(bounds.get("y", 0.25) * height)
    bw = int(bounds.get("w", 0.5) * width)
    bh = int(bounds.get("h", 0.5) * height)
    padding = int(min(bw, bh) * 0.15)
    bx = max(0, bx - padding)
    by = max(0, by - padding)
    bw = min(width - bx, bw + padding * 2)
    bh = min(height - by, bh + padding * 2)
    new_w = int(bw * scale)
    new_h = int(bh * scale)
    if new_w <= 0 or new_h <= 0:
        return frame

    region = frame[by : by + bh, bx : bx + bw]
    feather = max(5, int(min(bw, bh) * 0.1))
    mask_f = _scale_mask(state, bx, by, bw, bh, feather)
    region = region * mask_f
    scaled = F.interpolate(
        region.permute(2, 0, 1).unsqueeze(0),
        size=(new_h, new_w),
        mode="bilinear",
        align_corners=False,
    ).squeeze(0).permute(1, 2, 0)

    center_x = bx + bw // 2
    center_y = by + bh // 2
    paste_x = center_x - new_w // 2
    paste_y = center_y - new_h // 2
    result = frame.clone()
    y0 = max(paste_y, 0)
    x0 = max(paste_x, 0)
    y1 = min(paste_y + new_h, height)
    x1 = min(paste_x + new_w, width)
    sy0 = y0 - paste_y
    sx0 = x0 - paste_x
    if y1 > y0 and x1 > x0:
        patch = scaled[sy0 : sy0 + (y1 - y0), sx0 : sx0 + (x1 - x0)]
        result[y0:y1, x0:x1] = _alpha_composite(result[y0:y1, x0:x1], patch)
    return result


def _apply_element_glow_gpu(
    frame: Any,
    bounds: Dict[str, float],
    intensity: float,
    radius: float,
    color: Tuple[int, int, int],
    width: int,
    height: int,
    grid_y: Any,
    grid_x: Any,
    device: Any,
) -> Any:
    """Single outer ellipse + blur. Equivalent to the old max-stacked-ellipse loop, ~20x fewer kernels."""
    if intensity < 0.01:
        return frame
    torch, _ = _import_torch()
    scaled_radius = radius * preview_scale(width)
    if scaled_radius < 1:
        return frame
    i = int(scaled_radius)
    alpha = min(255, int(intensity * 100 * (i / scaled_radius))) / 255.0
    cx = bounds.get("center_x", 0.5) * width
    cy = bounds.get("center_y", 0.5) * height
    bw = bounds.get("w", 0.5) * width
    bh = bounds.get("h", 0.5) * height
    rx = max(bw / 2 + i, 1.0)
    ry = max(bh / 2 + i, 1.0)
    inside = ((grid_x - cx) / rx) ** 2 + ((grid_y - cy) / ry) ** 2 <= 1.0
    glow = torch.zeros(height, width, 4, device=device, dtype=frame.dtype)
    color_t = torch.tensor([c / 255.0 for c in color], device=device, dtype=frame.dtype)
    glow[..., :3] = color_t
    glow[..., 3] = inside.float() * alpha
    glow = _gaussian_blur_rgba(glow, scaled_radius / 3.0)
    return _alpha_composite(frame, glow)


def _apply_neon_outline_gpu(
    frame: Any,
    bounds: Dict[str, float],
    intensity: float,
    color: Tuple[int, int, int],
    line_width: float,
    glow_radius: float,
    width: int,
    height: int,
    grid_y: Any,
    grid_x: Any,
    device: Any,
) -> Any:
    if intensity < 0.01:
        return frame
    torch, _ = _import_torch()
    scale = preview_scale(width)
    x = bounds.get("x", 0.25) * width
    y = bounds.get("y", 0.25) * height
    w = bounds.get("w", 0.5) * width
    h = bounds.get("h", 0.5) * height
    cx = x + w / 2
    cy = y + h / 2
    rx = max(w / 2, 1.0)
    ry = max(h / 2, 1.0)
    lw = max(1.0, float(line_width) * scale)
    glow = max(1.0, float(glow_radius) * scale)
    ellipse = torch.sqrt(((grid_x - cx) / rx) ** 2 + ((grid_y - cy) / ry) ** 2)
    dist = torch.abs(ellipse - 1.0) * ((rx + ry) / 2)
    ring = (1.0 - dist / lw).clamp(min=0.0)
    overlay = torch.zeros(height, width, 4, device=device, dtype=frame.dtype)
    overlay[..., :3] = torch.tensor([c / 255.0 for c in color], device=device, dtype=frame.dtype)
    overlay[..., 3] = ring * intensity
    overlay = _gaussian_blur_rgba(overlay, glow / 2.0)
    return _alpha_composite(frame, overlay)


def _apply_vignette_gpu(frame: Any, strength: float, dist_sq: Any) -> Any:
    if strength < 0.01:
        return frame
    torch, _ = _import_torch()
    vignette = (1.0 - dist_sq * strength).clamp(0, 1).unsqueeze(-1)
    out_rgb = frame[..., :3] * (0.3 + 0.7 * vignette)
    return torch.cat([out_rgb, frame[..., 3:4]], dim=-1)


def _apply_film_grain_gpu(
    frame: Any, intensity: float, grain_size: float, width: int, height: int, device: Any,
) -> Any:
    if intensity < 0.01:
        return frame
    torch, _ = _import_torch()
    scale = preview_scale(width)
    block = max(1, int(grain_size * scale))
    small_w = max(1, width // block)
    small_h = max(1, height // block)
    noise = torch.randint(0, 256, (small_h, small_w), device=device, dtype=torch.float32)
    noise = noise.repeat_interleave(block, 0).repeat_interleave(block, 1)[:height, :width] / 255.0
    alpha = intensity * 0.25
    overlay = torch.stack([noise, noise, noise, torch.full_like(noise, alpha)], dim=-1)
    return _alpha_composite(frame, overlay)


def _apply_strobe_gpu(frame: Any, intensity: float, color: Tuple[int, int, int]) -> Any:
    if intensity < 0.01:
        return frame
    torch, _ = _import_torch()
    flash = torch.zeros_like(frame)
    flash[..., :3] = torch.tensor([c / 255.0 for c in color], device=frame.device, dtype=frame.dtype)
    flash[..., 3] = intensity * 0.7
    return _alpha_composite(frame, flash)


def _apply_chromatic_glitch_gpu(
    frame: Any,
    chromatic: float,
    rgb_split: float,
    scan_lines: bool,
    scan_opacity: float,
    width: int,
    height: int,
) -> Any:
    torch, _ = _import_torch()
    scale = preview_scale(width)
    split_px = max(chromatic, rgb_split) * scale
    offset = max(int(round(split_px)), int(round(2 * scale)))
    if offset <= 0:
        return frame
    out = frame.clone()
    r = frame[..., 0]
    b = frame[..., 2]
    out[..., 0] = 0
    out[..., 2] = 0
    if offset < width:
        out[:, : width - offset, 0] = r[:, offset:]
        out[:, offset:, 2] = b[:, : width - offset]
    if scan_lines and scan_opacity > 0.01:
        line_step = max(2, int(round(4 * scale)))
        line_height = max(1, int(round(2 * scale)))
        for y in range(0, height, line_step):
            out[y : y + line_height, :, :3] *= (1.0 - scan_opacity)
    return out


def _apply_slice_glitch_gpu(
    frame: Any, offset_px: float, width: int, height: int, seed: float,
) -> Any:
    scale = preview_scale(width)
    split_px = offset_px * scale
    if split_px <= 0:
        return frame
    result = frame.clone()
    slice_h = max(1, height // 8)
    for i in range(0, 8, 2):
        y0 = i * slice_h
        y1 = min((i + 1) * slice_h, height)
        x = math.sin(seed * 0.001 + i * 12.9898) * 43758.5453
        frac = x - math.floor(x)
        displacement = int(round((frac - 0.5) * split_px * 4))
        if displacement == 0:
            continue
        band = result[y0:y1].clone()
        shifted = band.new_zeros(band.shape)
        if displacement > 0:
            if displacement < width:
                shifted[:, displacement:] = band[:, : width - displacement]
        else:
            if -displacement < width:
                shifted[:, : width + displacement] = band[:, -displacement:]
        result[y0:y1] = shifted
    return result


def _spawn_particles(cpu_state: FrameRenderState, effects: Dict[str, Any], time_sec: float, width: int, height: int) -> None:
    bursts = effects.get("particle_bursts", [])
    burst_params = effects.get("particle_burst_params", {})
    for burst in bursts:
        burst_id = (
            burst.get("trigger_time"),
            burst.get("bounds_x", 0.25),
            burst.get("bounds_y", 0.25),
        )
        if burst_id in cpu_state.previous_bursts:
            continue
        cpu_state.previous_bursts.add(burst_id)
        cpu_state.particle_system.spawn_burst_from_bounds(
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


def _cpu_overlay_effects(
    frame: Any,
    cpu_state: FrameRenderState,
    effects: Dict[str, Any],
    time_sec: float,
    dt: float,
    width: int,
    height: int,
    device: Any,
) -> Any:
    """One GPU→CPU→GPU round-trip for particle / trail / flare drawing."""
    _spawn_particles(cpu_state, effects, time_sec, width, height)
    cpu_state.particle_system.update(time_sec, dt)
    need_trails = effects.get("energy_trails_enabled", False)
    flare_intensity = effects.get("light_flares_intensity", 0)
    need_flares = flare_intensity > 0.01
    need_particles = bool(cpu_state.particle_system.particles)
    if not (need_trails or need_flares or need_particles):
        return frame

    pil_frame = _tensor_to_pil_rgba(frame)
    if need_particles:
        pil_frame = cpu_state.particle_system.draw(pil_frame, time_sec)
    if need_trails:
        pil_frame = apply_energy_trails(
            pil_frame, effects.get("energy_trails_params", {}), width, height,
        )
    if need_flares:
        pil_frame = apply_light_flares(
            pil_frame,
            effects.get("light_flares_points", []),
            flare_intensity,
            effects.get("light_flares_size", 100),
            effects.get("light_flares_colors", [(255, 255, 200)]),
            width, height,
        )
    return _pil_rgba_to_tensor(pil_frame, device)


def _render_frame_tensor(
    state: GpuFrameRenderState,
    effect_params: EffectParameters,
    time_sec: float,
    dt: float,
    effects: Optional[Dict[str, Any]] = None,
) -> Any:
    if effects is None:
        effects = get_effect_value_at_time(effect_params, time_sec)

    cpu_state = state.cpu_state
    bounds = effects.get("subject_bounds", cpu_state.bounds_dict)
    width, height = cpu_state.width, cpu_state.height
    device = state.device

    frame = (
        state.background_dim_tensor
        if cpu_state.bg_dim_enabled
        else state.base_tensor
    ).clone()

    for ripple in effects.get("ripple_waves", []):
        frame = _apply_ripple_gpu(
            frame, ripple, effects.get("ripple_intensity", 0.5),
            width, height, state.grid_y, state.grid_x, device,
        )

    scale = effects.get("element_scale", 1.0)
    if abs(scale - 1.0) > 0.001:
        frame = _apply_element_scale_gpu(state, frame, bounds, scale, width, height)

    glow_intensity = effects.get("element_glow_intensity", 0)
    if glow_intensity > 0.01:
        frame = _apply_element_glow_gpu(
            frame, bounds, glow_intensity,
            effects.get("element_glow_radius", 50),
            effects.get("element_glow_color", (255, 200, 100)),
            width, height, state.grid_y, state.grid_x, device,
        )

    neon_intensity = effects.get("neon_outline_intensity", 0)
    if neon_intensity > 0.01:
        frame = _apply_neon_outline_gpu(
            frame, bounds, neon_intensity,
            effects.get("neon_outline_color", (0, 255, 255)),
            effects.get("neon_outline_width", 3),
            effects.get("neon_outline_glow", 15),
            width, height, state.grid_y, state.grid_x, device,
        )

    frame = _cpu_overlay_effects(
        frame, cpu_state, effects, time_sec, dt, width, height, device,
    )

    vignette_strength = effects.get("vignette_strength", 0)
    if vignette_strength > 0.01:
        frame = _apply_vignette_gpu(frame, vignette_strength, state.vignette_dist_sq)

    if effects.get("film_grain_enabled", False):
        frame = _apply_film_grain_gpu(
            frame,
            effects.get("film_grain_intensity", 0.2),
            effects.get("film_grain_size", 1.5),
            width, height, device,
        )

    if effects.get("strobe_active", False):
        frame = _apply_strobe_gpu(
            frame,
            effects.get("strobe_intensity", 0.5),
            effects.get("strobe_color", (255, 255, 255)),
        )

    if effects.get("glitch_active", False):
        frame = _apply_chromatic_glitch_gpu(
            frame,
            effects.get("glitch_chromatic", 0),
            effects.get("glitch_rgb_split", 0),
            effects.get("glitch_scan_lines", False),
            effects.get("glitch_scan_opacity", 0),
            width, height,
        )

    if effects.get("glitch_slice_active", False):
        frame = _apply_slice_glitch_gpu(
            frame,
            effects.get("glitch_slice_offset", 0),
            width, height,
            effects.get("glitch_slice_seed", 0),
        )

    return frame


def render_single_frame_gpu(
    state: GpuFrameRenderState,
    effect_params: EffectParameters,
    time_sec: float,
    dt: float,
    effects: Optional[Dict[str, Any]] = None,
) -> Image.Image:
    """Render one frame on GPU; returns RGBA PIL image (parity tests / debug)."""
    tensor = _render_frame_tensor(state, effect_params, time_sec, dt, effects)
    return _tensor_to_pil_rgba(tensor)


def render_video_gpu(
    image_path: str,
    audio_path: str,
    output_path: str,
    effect_params: EffectParameters,
    render_settings: RenderSettings,
    audio_start: float = 0.0,
    progress_callback: Optional[Callable[[float], None]] = None,
    custom_particle_sprite: Optional[str] = None,
) -> str:
    """GPU export path — same signature as render_video()."""
    _log_device_once()
    torch, _ = _import_torch()

    width, height, resampling = resolve_render_dimensions(render_settings)
    fps = render_settings.fps
    duration = render_settings.duration
    total_frames = int(duration * fps)

    base_image = Image.open(image_path).convert("RGBA")
    base_image = fit_image_to_frame(base_image, width, height, resampling)

    gpu_state = prepare_gpu_frame_render_state(
        base_image, effect_params, width, height, resampling,
        custom_particle_sprite=custom_particle_sprite,
    )

    render_start = time.perf_counter()
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
        with torch.inference_mode():
            for frame_num in range(total_frames):
                time_sec = frame_num / fps
                dt = 1.0 / fps

                if frame_num % 100 == 0:
                    elapsed = time.perf_counter() - render_start
                    fps_so_far = frame_num / elapsed if elapsed > 0.5 else 0.0
                    print(
                        f"[render_video] frame {frame_num}/{total_frames} "
                        f"({elapsed:.0f}s elapsed, {fps_so_far:.1f} fps)"
                    )

                frame_tensor = _render_frame_tensor(
                    gpu_state, effect_params, time_sec, dt,
                )
                encoder.write_rgb_bytes(_tensor_to_rgb_bytes(frame_tensor))

                if progress_callback:
                    progress_callback((frame_num + 1) / total_frames * 0.9)

        if progress_callback:
            progress_callback(0.95)

        encoder_name, _encode_elapsed = encoder.finish()
    except Exception:
        encoder.abort()
        raise

    total_elapsed = time.perf_counter() - render_start
    device_label = get_cuda_device_name() or "CUDA"
    out_fps = total_frames / total_elapsed if total_elapsed > 0 else 0.0
    print(
        f"[render_video] renderer=gpu device={device_label} "
        f"{total_frames} frames @ {width}x{height} "
        f"encoder={encoder_name}: "
        f"total={total_elapsed:.1f}s ({out_fps:.1f} fps, streamed encode)"
    )

    if progress_callback:
        progress_callback(1.0)

    return output_path
