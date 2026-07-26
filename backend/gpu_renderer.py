"""
GPU-accelerated video renderer using PyTorch CUDA.
Optional dependency: pip install -r requirements-gpu.txt
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
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
    apply_film_grain,
    apply_neon_outline,
    apply_chromatic_glitch,
    apply_slice_glitch,
    apply_ripple_wave,
)

_torch = None
_F = None
_tv_gaussian_blur = None
_device_name_logged = False


def _import_torch():
    global _torch, _F, _tv_gaussian_blur
    if _torch is None:
        import torch
        import torch.nn.functional as F
        from torchvision.transforms.functional import gaussian_blur

        _torch = torch
        _F = F
        _tv_gaussian_blur = gaussian_blur
    return _torch, _F, _tv_gaussian_blur


def cuda_available() -> bool:
    try:
        torch, _, _ = _import_torch()
        return torch.cuda.is_available()
    except ImportError:
        return False


def get_cuda_device_name() -> Optional[str]:
    if not cuda_available():
        return None
    torch, _, _ = _import_torch()
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
        # Distinguish missing torch vs CPU-only torch for clearer logs.
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


def _pil_rgba_to_tensor(img: Image.Image, device: Any) -> Any:
    torch, _, _ = _import_torch()
    arr = np.asarray(img.convert("RGBA"), dtype=np.float32) / 255.0
    return torch.from_numpy(arr).to(device)


def _tensor_to_pil_rgba(tensor: Any) -> Image.Image:
    arr = (tensor.detach().cpu().clamp(0, 1).numpy() * 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGBA")


def _alpha_composite(base: Any, overlay: Any) -> Any:
    torch, _, _ = _import_torch()
    oa = overlay[..., 3:4]
    ba = base[..., 3:4]
    out_a = oa + ba * (1 - oa)
    out_rgb = overlay[..., :3] * oa + base[..., :3] * ba * (1 - oa)
    out_rgb = out_rgb / torch.clamp(out_a, min=1e-6)
    return torch.cat([out_rgb, out_a], dim=-1)


def _gaussian_blur_rgba(tensor: Any, radius: float) -> Any:
    if radius < 0.1:
        return tensor
    _, _, gaussian_blur = _import_torch()
    ksize = max(3, int(radius * 2) | 1)
    ksize = min(ksize, 51)
    sigma = max(radius / 3.0, 0.1)
    chw = tensor.permute(2, 0, 1).unsqueeze(0)
    blurred = gaussian_blur(chw, kernel_size=[ksize, ksize], sigma=[sigma, sigma])
    return blurred.squeeze(0).permute(1, 2, 0)


def _build_ellipse_mask_gpu(
    height: int, width: int, cx: float, cy: float, rx: float, ry: float, device: Any,
) -> Any:
    torch, _, _ = _import_torch()
    y = torch.arange(height, device=device, dtype=torch.float32)
    x = torch.arange(width, device=device, dtype=torch.float32)
    yy, xx = torch.meshgrid(y, x, indexing="ij")
    return ((xx - cx) / max(rx, 1.0)) ** 2 + ((yy - cy) / max(ry, 1.0)) ** 2 <= 1.0


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
    torch, _, _ = _import_torch()
    device = torch.device("cuda")
    base_tensor = _pil_rgba_to_tensor(cpu_state.base_image, device)
    bg_tensor = _pil_rgba_to_tensor(cpu_state.background_dim_base, device)
    dist_sq = torch.from_numpy(cpu_state.vignette_dist_sq).to(device)
    return GpuFrameRenderState(
        cpu_state=cpu_state,
        device=device,
        base_tensor=base_tensor,
        background_dim_tensor=bg_tensor,
        vignette_dist_sq=dist_sq,
    )


def _apply_ripple_gpu(
    frame: Any,
    ripple: Dict[str, Any],
    width: int,
    height: int,
    intensity: float,
    device: Any,
) -> Any:
    if intensity < 0.01:
        return frame
    pil_frame = _tensor_to_pil_rgba(frame)
    pil_frame = apply_ripple_wave(pil_frame, ripple, width, height, intensity)
    return _pil_rgba_to_tensor(pil_frame, device)


def _apply_element_scale_gpu(
    frame: Any,
    bounds: Dict[str, float],
    scale: float,
    width: int,
    height: int,
    device: Any,
) -> Any:
    if abs(scale - 1.0) < 0.001:
        return frame
    torch, F, _ = _import_torch()

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

    region = frame[by : by + bh, bx : bx + bw].clone()
    y = torch.arange(bh, device=device, dtype=torch.float32)
    x = torch.arange(bw, device=device, dtype=torch.float32)
    yy, xx = torch.meshgrid(y, x, indexing="ij")
    mask = ((xx / max(bw - 1, 1) - 0.5) * 2) ** 2 + ((yy / max(bh - 1, 1) - 0.5) * 2) ** 2 <= 1.0
    feather = max(5, int(min(bw, bh) * 0.1))
    mask_f = mask.float().unsqueeze(-1)
    mask_f = _gaussian_blur_rgba(
        torch.cat([mask_f, mask_f, mask_f, torch.ones_like(mask_f)], dim=-1),
        feather,
    )[..., 3:4]
    region = region * mask_f + region * (1 - mask_f) * 0.0
    region[..., 3:4] = region[..., 3:4] * mask_f

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
    sy1 = sy0 + (y1 - y0)
    sx1 = sx0 + (x1 - x0)
    if y1 > y0 and x1 > x0:
        patch = scaled[sy0:sy1, sx0:sx1]
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
    device: Any,
) -> Any:
    if intensity < 0.01:
        return frame
    torch, _, _ = _import_torch()

    scaled_radius = radius * preview_scale(width)
    cx = bounds.get("center_x", 0.5) * width
    cy = bounds.get("center_y", 0.5) * height
    bw = bounds.get("w", 0.5) * width
    bh = bounds.get("h", 0.5) * height
    y = torch.arange(height, device=device, dtype=torch.float32)
    x = torch.arange(width, device=device, dtype=torch.float32)
    yy, xx = torch.meshgrid(y, x, indexing="ij")
    glow = torch.zeros(height, width, 4, device=device)
    step = max(3, int(5 * preview_scale(width)))
    color_t = torch.tensor([c / 255.0 for c in color], device=device)

    for i in range(int(scaled_radius), 0, -step):
        alpha = min(255, int(intensity * 100 * (i / scaled_radius))) / 255.0
        rx = bw / 2 + i
        ry = bh / 2 + i
        inside = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0
        for c in range(3):
            glow[..., c] = torch.where(
                inside, torch.maximum(glow[..., c], color_t[c]), glow[..., c],
            )
        glow[..., 3] = torch.where(
            inside, torch.maximum(glow[..., 3], torch.tensor(alpha, device=device)), glow[..., 3],
        )

    glow = _gaussian_blur_rgba(glow, scaled_radius / 3)
    return _alpha_composite(frame, glow)


def _apply_vignette_gpu(frame: Any, strength: float, dist_sq: Any) -> Any:
    if strength < 0.01:
        return frame
    torch, _, _ = _import_torch()
    vignette = 1.0 - dist_sq * strength
    vignette = vignette.clamp(0, 1).unsqueeze(-1)
    darkened = frame.clone()
    darkened[..., :3] *= 0.3
    out_rgb = frame[..., :3] * vignette + darkened[..., :3] * (1 - vignette)
    return torch.cat([out_rgb, frame[..., 3:4]], dim=-1)


def _apply_strobe_gpu(frame: Any, intensity: float, color: Tuple[int, int, int]) -> Any:
    if intensity < 0.01:
        return frame
    torch, _, _ = _import_torch()
    alpha = intensity * 0.7
    flash = torch.zeros_like(frame)
    flash[..., :3] = torch.tensor([c / 255.0 for c in color], device=frame.device)
    flash[..., 3] = alpha
    return _alpha_composite(frame, flash)


def render_single_frame_gpu(
    state: GpuFrameRenderState,
    effect_params: EffectParameters,
    time_sec: float,
    dt: float,
    effects: Optional[Dict[str, Any]] = None,
) -> Image.Image:
    """Render one frame on GPU; returns RGBA PIL image for JPEG encode."""
    if effects is None:
        effects = get_effect_value_at_time(effect_params, time_sec)

    cpu_state = state.cpu_state
    bounds = effects.get("subject_bounds", cpu_state.bounds_dict)
    width, height = cpu_state.width, cpu_state.height
    device = state.device

    frame = (
        state.background_dim_tensor.clone()
        if cpu_state.bg_dim_enabled
        else state.base_tensor.clone()
    )

    ripples = effects.get("ripple_waves", [])
    for ripple in ripples:
        frame = _apply_ripple_gpu(
            frame, ripple, width, height, effects.get("ripple_intensity", 0.5), device,
        )

    scale = effects.get("element_scale", 1.0)
    if abs(scale - 1.0) > 0.001:
        frame = _apply_element_scale_gpu(frame, bounds, scale, width, height, device)

    glow_intensity = effects.get("element_glow_intensity", 0)
    if glow_intensity > 0.01:
        frame = _apply_element_glow_gpu(
            frame, bounds, glow_intensity,
            effects.get("element_glow_radius", 50),
            effects.get("element_glow_color", (255, 200, 100)),
            width, height, device,
        )

    neon_intensity = effects.get("neon_outline_intensity", 0)
    if neon_intensity > 0.01:
        pil_frame = _tensor_to_pil_rgba(frame)
        pil_frame = apply_neon_outline(
            pil_frame, bounds,
            neon_intensity,
            effects.get("neon_outline_color", (0, 255, 255)),
            effects.get("neon_outline_width", 3),
            effects.get("neon_outline_glow", 15),
            width, height,
        )
        frame = _pil_rgba_to_tensor(pil_frame, device)

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

    cpu_state.particle_system.update(time_sec, dt)
    if cpu_state.particle_system.particles:
        pil_frame = _tensor_to_pil_rgba(frame)
        pil_frame = cpu_state.particle_system.draw(pil_frame, time_sec)
        frame = _pil_rgba_to_tensor(pil_frame, device)

    if effects.get("energy_trails_enabled", False):
        pil_frame = _tensor_to_pil_rgba(frame)
        pil_frame = apply_energy_trails(
            pil_frame, effects.get("energy_trails_params", {}), width, height,
        )
        frame = _pil_rgba_to_tensor(pil_frame, device)

    flare_intensity = effects.get("light_flares_intensity", 0)
    if flare_intensity > 0.01:
        pil_frame = _tensor_to_pil_rgba(frame)
        pil_frame = apply_light_flares(
            pil_frame,
            effects.get("light_flares_points", []),
            flare_intensity,
            effects.get("light_flares_size", 100),
            effects.get("light_flares_colors", [(255, 255, 200)]),
            width, height,
        )
        frame = _pil_rgba_to_tensor(pil_frame, device)

    vignette_strength = effects.get("vignette_strength", 0)
    if vignette_strength > 0.01:
        frame = _apply_vignette_gpu(frame, vignette_strength, state.vignette_dist_sq)

    if effects.get("film_grain_enabled", False):
        pil_frame = _tensor_to_pil_rgba(frame)
        pil_frame = apply_film_grain(
            pil_frame,
            effects.get("film_grain_intensity", 0.2),
            effects.get("film_grain_size", 1.5),
        )
        frame = _pil_rgba_to_tensor(pil_frame, device)

    if effects.get("strobe_active", False):
        frame = _apply_strobe_gpu(
            frame,
            effects.get("strobe_intensity", 0.5),
            effects.get("strobe_color", (255, 255, 255)),
        )

    if effects.get("glitch_active", False):
        pil_frame = _tensor_to_pil_rgba(frame)
        pil_frame = apply_chromatic_glitch(
            pil_frame,
            effects.get("glitch_chromatic", 0),
            effects.get("glitch_rgb_split", 0),
            effects.get("glitch_scan_lines", False),
            effects.get("glitch_scan_opacity", 0),
            width,
            height,
        )
        frame = _pil_rgba_to_tensor(pil_frame, device)

    if effects.get("glitch_slice_active", False):
        pil_frame = _tensor_to_pil_rgba(frame)
        pil_frame = apply_slice_glitch(
            pil_frame,
            effects.get("glitch_slice_offset", 0),
            width,
            height,
            effects.get("glitch_slice_seed", 0),
        )
        frame = _pil_rgba_to_tensor(pil_frame, device)

    return _tensor_to_pil_rgba(frame)


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
    _import_torch()

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
        for frame_num in range(total_frames):
            time_sec = frame_num / fps
            dt = 1.0 / fps

            if frame_num % 100 == 0:
                elapsed = time.perf_counter() - render_start
                print(
                    f"[render_video] frame {frame_num}/{total_frames} "
                    f"({elapsed:.0f}s elapsed)"
                )

            frame = render_single_frame_gpu(
                gpu_state, effect_params, time_sec, dt,
            )
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
    device_label = get_cuda_device_name() or "CUDA"
    print(
        f"[render_video] renderer=gpu device={device_label} "
        f"{total_frames} frames @ {width}x{height} "
        f"encoder={encoder_name}: "
        f"total={total_elapsed:.1f}s (streamed encode)"
    )

    if progress_callback:
        progress_callback(1.0)

    return output_path
