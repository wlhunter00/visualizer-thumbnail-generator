#!/usr/bin/env python3
"""
Demo Video Generation Script
Generates 30-second demo videos for each of the 13 effects at max intensity.
Videos are saved to backend/demos/ folder.

Usage:
    python generate_demos.py
"""

import json
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from audio_analysis import analyze_audio
from effect_engine import (
    EffectToggles, EffectToggle, ImageContext, SubjectBounds,
    calculate_effect_parameters
)
from video_renderer import render_video, RenderSettings, AspectRatio


# Configuration
AUDIO_START_TIME = 63.0  # Start at 1:03
DURATION = 30.0          # 30 second clips
INTENSITY = 1.0          # Max intensity for demos
FPS = 24                 # Preview quality FPS
ASPECT_RATIO = AspectRatio.VERTICAL  # 9:16 for demos

# Paths
SCRIPT_DIR = Path(__file__).parent
DEMO_ASSETS_DIR = SCRIPT_DIR.parent / "demo-assets"
DEMOS_OUTPUT_DIR = SCRIPT_DIR / "demos"

# Demo asset files
IMAGE_FILE = DEMO_ASSETS_DIR / "cd698111-ec93-45d9-8296-b870879fcef4 (1) copy.png"
AUDIO_FILE = DEMO_ASSETS_DIR / "How to Save a Life Mashup copy.mp3"


@dataclass
class EffectInfo:
    """Information about an effect for the manifest."""
    key: str
    name: str
    description: str
    category: str
    explanation: str


@dataclass
class PresetInfo:
    """Information about a curated effect preset."""
    key: str
    name: str
    description: str
    category: str  # genre, mood, intensity, platform
    explanation: str
    effects: dict  # effect_key -> intensity (0.0-1.0)


# All 13 single effects with their metadata
SINGLE_EFFECTS = [
    EffectInfo(
        key="element_glow",
        name="Element Glow",
        description="Subject emits pulsating light",
        category="element",
        explanation="Emits warm, pulsating light from your subject on beats. The glow intensifies with beat strength, creating a breathing effect that makes your subject feel alive with the music."
    ),
    EffectInfo(
        key="element_scale",
        name="Scale Pulse",
        description="Subject grows/shrinks on beats",
        category="element",
        explanation="Makes your subject pulse larger on each beat, creating a breathing or pumping effect. Stronger beats cause bigger scale changes, syncing the visual impact directly to the music's energy."
    ),
    EffectInfo(
        key="neon_outline",
        name="Neon Outline",
        description="Glowing edge around subject",
        category="element",
        explanation="Draws a glowing, colored edge around your subject that pulses brighter on beats. Creates an 80s retro or cyberpunk aesthetic perfect for electronic and synthwave tracks."
    ),
    EffectInfo(
        key="echo_trail",
        name="Echo Trail",
        description="Ghostly afterimage effect",
        category="element",
        explanation="Creates ghostly afterimages that trail behind your subject, producing a motion blur or 'speed lines' effect even on static images. Great for adding a sense of movement and energy."
    ),
    EffectInfo(
        key="particle_burst",
        name="Particle Burst",
        description="Particles explode on beats",
        category="particle",
        explanation="Explodes particles outward from your subject on strong beats. Particles inherit colors from your image and gracefully fade as they drift, creating celebratory burst effects."
    ),
    EffectInfo(
        key="energy_trails",
        name="Energy Trails",
        description="Glowing lines orbit subject",
        category="particle",
        explanation="Orbiting light trails that circle around your subject continuously. Speed syncs with the tempo for a hypnotic spiral effect that adds constant motion and energy."
    ),
    EffectInfo(
        key="light_flares",
        name="Light Flares",
        description="Lens flare from bright spots",
        category="particle",
        explanation="Adds cinematic lens flares at bright spots in your image. Flares intensify on powerful beats for dramatic emphasis, mimicking professional camera effects."
    ),
    EffectInfo(
        key="glitch",
        name="Glitch",
        description="RGB split and distortion",
        category="style",
        explanation="Digital distortion with RGB color splitting, scan lines, and random slice displacement. Triggers on sharp transients for a broken, corrupted, or cyberpunk aesthetic."
    ),
    EffectInfo(
        key="ripple_wave",
        name="Ripple Wave",
        description="Distortion waves from center",
        category="style",
        explanation="Sends circular distortion waves outward from the subject on beats, like dropping a stone in water. Creates a shockwave effect that pulses with the rhythm."
    ),
    EffectInfo(
        key="film_grain",
        name="Film Grain",
        description="VHS/retro texture",
        category="style",
        explanation="Adds analog noise texture over the entire frame for a vintage film or VHS camcorder aesthetic. Perfect for lo-fi, nostalgic, or retro-themed content."
    ),
    EffectInfo(
        key="strobe_flash",
        name="Strobe Flash",
        description="Brief flashes on strong beats",
        category="style",
        explanation="Brief white flashes on the strongest beats only. Use sparingly for high-energy, club-style visuals. Creates dramatic impact on drops and climactic moments."
    ),
    EffectInfo(
        key="vignette_pulse",
        name="Vignette Pulse",
        description="Dark edges pulse with rhythm",
        category="style",
        explanation="Darkens the edges of the frame and pulses them with the rhythm, drawing focus to the center while adding cinematic depth. Subtle but effective for mood."
    ),
    EffectInfo(
        key="background_dim",
        name="Background Dim",
        description="Darken background for contrast",
        category="background",
        explanation="Darkens and optionally blurs the background behind your subject, making them pop and creating depth separation. Essential for making your subject stand out."
    ),
]


# 30 Curated Presets - combinations of effects for different styles
PRESETS = [
    # === GENRE/MOOD PRESETS ===
    PresetInfo(
        key="preset_clean_minimal",
        name="Clean & Minimal",
        description="Subtle glow with gentle vignette",
        category="mood",
        explanation="A refined, understated look perfect for acoustic tracks, podcasts, or professional content. The soft glow adds warmth without overwhelming the visuals.",
        effects={"element_glow": 0.4, "vignette_pulse": 0.3, "background_dim": 0.2}
    ),
    PresetInfo(
        key="preset_lofi_chill",
        name="Lo-Fi Chill",
        description="Vintage vibes with film grain",
        category="mood",
        explanation="That cozy, nostalgic aesthetic perfect for lo-fi hip hop, chillwave, or study beats. The film grain adds analog warmth while the vignette creates intimacy.",
        effects={"film_grain": 0.5, "vignette_pulse": 0.4, "background_dim": 0.3, "element_glow": 0.3}
    ),
    PresetInfo(
        key="preset_high_energy_edm",
        name="High Energy EDM",
        description="Explosive particles and strobes",
        category="genre",
        explanation="Maximum impact for drops and buildups. Particles explode on every beat while strobes punctuate the biggest moments. Perfect for EDM, dubstep, and festival tracks.",
        effects={"particle_burst": 1.0, "strobe_flash": 0.7, "element_scale": 0.8, "glitch": 0.5, "vignette_pulse": 0.6}
    ),
    PresetInfo(
        key="preset_synthwave",
        name="Synthwave Retro",
        description="Neon outlines with retro grain",
        category="genre",
        explanation="Channel the 80s with glowing neon edges and analog texture. Ideal for synthwave, retrowave, and anything with that nostalgic electronic feel.",
        effects={"neon_outline": 0.9, "film_grain": 0.3, "vignette_pulse": 0.5, "element_glow": 0.4, "background_dim": 0.4}
    ),
    PresetInfo(
        key="preset_dreamy_ambient",
        name="Dreamy Ambient",
        description="Soft glow with ethereal trails",
        category="mood",
        explanation="A floaty, otherworldly aesthetic for ambient, new age, or meditation music. Echo trails create a sense of movement while the glow adds warmth.",
        effects={"element_glow": 0.6, "echo_trail": 0.7, "background_dim": 0.4, "vignette_pulse": 0.3, "ripple_wave": 0.3}
    ),
    PresetInfo(
        key="preset_club_rave",
        name="Club / Rave",
        description="Strobes, glitch, and chaos",
        category="genre",
        explanation="Recreate the club experience with intense strobes and glitchy distortion. Best for techno, house, and high-BPM dance tracks.",
        effects={"strobe_flash": 0.8, "glitch": 0.7, "particle_burst": 0.6, "energy_trails": 0.5, "element_scale": 0.5}
    ),
    PresetInfo(
        key="preset_cinematic",
        name="Cinematic Epic",
        description="Lens flares with dramatic vignette",
        category="mood",
        explanation="Hollywood-style visuals with professional lens flares and deep contrast. Perfect for orchestral, trailer music, or epic compositions.",
        effects={"light_flares": 0.8, "vignette_pulse": 0.7, "background_dim": 0.5, "element_glow": 0.4, "element_scale": 0.3}
    ),
    PresetInfo(
        key="preset_cyberpunk",
        name="Cyberpunk",
        description="Neon, glitch, and energy trails",
        category="genre",
        explanation="Dystopian future aesthetics with corrupted data and neon lights. Great for industrial, darksynth, or cyberpunk-themed content.",
        effects={"neon_outline": 0.8, "glitch": 0.6, "energy_trails": 0.7, "background_dim": 0.5, "vignette_pulse": 0.4}
    ),
    PresetInfo(
        key="preset_psychedelic",
        name="Psychedelic Trip",
        description="Ripples, trails, and swirling energy",
        category="mood",
        explanation="Mind-bending visuals with distortion waves and hypnotic motion. Ideal for psytrance, experimental, or trippy electronic music.",
        effects={"ripple_wave": 0.9, "energy_trails": 0.8, "echo_trail": 0.7, "element_glow": 0.5, "glitch": 0.3}
    ),
    PresetInfo(
        key="preset_gentle_pop",
        name="Gentle Pop",
        description="Subtle pulse with warm glow",
        category="genre",
        explanation="Clean and inviting for pop, indie, or singer-songwriter tracks. The gentle scale pulse adds life without being distracting.",
        effects={"element_scale": 0.4, "element_glow": 0.5, "vignette_pulse": 0.3, "background_dim": 0.2}
    ),
    
    # === EFFECT-FOCUSED COMBOS ===
    PresetInfo(
        key="preset_full_glow",
        name="Full Glow Package",
        description="All the light effects combined",
        category="combo",
        explanation="Maximum luminosity with every glow effect working together. The subject radiates light from within while lens flares add cinematic sparkle.",
        effects={"element_glow": 0.9, "neon_outline": 0.7, "light_flares": 0.8, "background_dim": 0.4}
    ),
    PresetInfo(
        key="preset_motion_heavy",
        name="Motion Heavy",
        description="Scale, trails, and ripples",
        category="combo",
        explanation="Everything moves and pulses. Creates a dynamic, breathing composition where nothing stays still. Great for energetic tracks.",
        effects={"element_scale": 0.8, "echo_trail": 0.7, "ripple_wave": 0.8, "energy_trails": 0.5}
    ),
    PresetInfo(
        key="preset_particle_party",
        name="Particle Party",
        description="All particle effects at once",
        category="combo",
        explanation="A celebration of particles - bursts explode outward, trails orbit around, and flares sparkle. Perfect for drops and climactic moments.",
        effects={"particle_burst": 0.9, "energy_trails": 0.8, "light_flares": 0.7, "element_glow": 0.4}
    ),
    PresetInfo(
        key="preset_distortion_mix",
        name="Distortion Mix",
        description="Glitch, ripple, and echo combined",
        category="combo",
        explanation="Reality breaks down with layered distortion effects. The image glitches, ripples, and trails create an unstable, chaotic feel.",
        effects={"glitch": 0.8, "ripple_wave": 0.7, "echo_trail": 0.6, "vignette_pulse": 0.4}
    ),
    PresetInfo(
        key="preset_vintage_complete",
        name="Vintage Complete",
        description="Full retro treatment",
        category="combo",
        explanation="Transport viewers to another era with film grain, warm vignette, and subtle strobes mimicking old projector flicker.",
        effects={"film_grain": 0.6, "vignette_pulse": 0.6, "strobe_flash": 0.2, "background_dim": 0.3, "element_glow": 0.3}
    ),
    
    # === INTENSITY LEVELS ===
    PresetInfo(
        key="preset_subtle_pro",
        name="Subtle & Professional",
        description="Barely-there enhancements",
        category="intensity",
        explanation="So subtle you almost don't notice it, but everything looks better. Perfect for corporate content, interviews, or when you need polish without flash.",
        effects={"background_dim": 0.2, "vignette_pulse": 0.2, "element_glow": 0.2}
    ),
    PresetInfo(
        key="preset_medium_energy",
        name="Medium Energy",
        description="Balanced effect intensity",
        category="intensity",
        explanation="The Goldilocks zone - enough visual interest to be engaging without overwhelming the content. Works well for most music genres.",
        effects={"element_glow": 0.5, "element_scale": 0.4, "particle_burst": 0.5, "vignette_pulse": 0.4, "background_dim": 0.3}
    ),
    PresetInfo(
        key="preset_maximum_chaos",
        name="Maximum Chaos",
        description="Every effect at high intensity",
        category="intensity",
        explanation="Absolute sensory overload. Every effect cranked up for maximum visual impact. Use sparingly - best for drops, breakdowns, or experimental content.",
        effects={
            "element_glow": 0.9, "element_scale": 0.8, "neon_outline": 0.7, "echo_trail": 0.6,
            "particle_burst": 1.0, "energy_trails": 0.8, "light_flares": 0.7,
            "glitch": 0.6, "ripple_wave": 0.5, "strobe_flash": 0.5, "vignette_pulse": 0.7, "background_dim": 0.5
        }
    ),
    
    # === PLATFORM-SPECIFIC ===
    PresetInfo(
        key="preset_tiktok_viral",
        name="TikTok Viral",
        description="Eye-catching for short-form",
        category="platform",
        explanation="Optimized for the TikTok algorithm - high contrast, quick visual payoff, and attention-grabbing effects that pop in the first second.",
        effects={"glitch": 0.6, "strobe_flash": 0.5, "particle_burst": 0.8, "element_scale": 0.6, "neon_outline": 0.5}
    ),
    PresetInfo(
        key="preset_youtube_lyric",
        name="YouTube Lyric Video",
        description="Clean background for text overlay",
        category="platform",
        explanation="Designed to be a backdrop for lyrics or text. The dimmed, subtly animated background keeps attention on your words without being boring.",
        effects={"background_dim": 0.5, "element_glow": 0.3, "vignette_pulse": 0.4, "element_scale": 0.2}
    ),
    PresetInfo(
        key="preset_instagram_story",
        name="Instagram Story",
        description="Bold and shareable",
        category="platform",
        explanation="Made for the gram - vibrant effects that look great in vertical format and encourage shares and saves.",
        effects={"neon_outline": 0.7, "particle_burst": 0.6, "energy_trails": 0.5, "background_dim": 0.4, "element_glow": 0.5}
    ),
    
    # === CREATIVE/THEMED ===
    PresetInfo(
        key="preset_underwater",
        name="Underwater",
        description="Rippling, glowing depths",
        category="theme",
        explanation="Evokes being submerged with gentle ripples and ethereal glow. Perfect for dreamy, aquatic, or introspective moods.",
        effects={"ripple_wave": 0.8, "element_glow": 0.5, "background_dim": 0.4, "vignette_pulse": 0.4, "echo_trail": 0.3}
    ),
    PresetInfo(
        key="preset_electric_storm",
        name="Electric Storm",
        description="Flares, strobes, and chaos",
        category="theme",
        explanation="Lightning strikes and electrical discharge. Intense, unpredictable energy for powerful, aggressive music.",
        effects={"light_flares": 0.9, "strobe_flash": 0.7, "glitch": 0.6, "energy_trails": 0.7, "element_scale": 0.5}
    ),
    PresetInfo(
        key="preset_soft_focus",
        name="Soft Focus",
        description="Dreamy blur with gentle glow",
        category="theme",
        explanation="Everything feels slightly out of focus in the best way. Romantic, nostalgic, and intimate. Great for ballads and love songs.",
        effects={"background_dim": 0.6, "element_glow": 0.5, "vignette_pulse": 0.5, "echo_trail": 0.4}
    ),
    PresetInfo(
        key="preset_neon_nights",
        name="Neon Nights",
        description="City lights aesthetic",
        category="theme",
        explanation="Late night in the city with neon signs and light trails. Urban, modern, and slightly mysterious.",
        effects={"neon_outline": 0.8, "energy_trails": 0.7, "particle_burst": 0.5, "background_dim": 0.5, "vignette_pulse": 0.4}
    ),
    PresetInfo(
        key="preset_glitch_art",
        name="Glitch Art",
        description="Intentionally broken aesthetic",
        category="theme",
        explanation="Embrace the digital artifacts. Glitch art meets music visualization for an experimental, avant-garde look.",
        effects={"glitch": 0.9, "echo_trail": 0.6, "film_grain": 0.4, "ripple_wave": 0.3}
    ),
    PresetInfo(
        key="preset_epic_drop",
        name="Epic Drop",
        description="Build to maximum impact",
        category="theme",
        explanation="Designed for the drop - when the beat hits, everything explodes. Scale pulse, particle burst, strobes, and ripples all fire together.",
        effects={"strobe_flash": 0.8, "element_scale": 0.9, "particle_burst": 1.0, "ripple_wave": 0.7, "vignette_pulse": 0.6}
    ),
    PresetInfo(
        key="preset_cozy_acoustic",
        name="Cozy Acoustic",
        description="Warm and intimate",
        category="theme",
        explanation="Like being in a small coffee shop venue. Warm grain, soft vignette, and gentle glow create an intimate, live performance feel.",
        effects={"film_grain": 0.3, "vignette_pulse": 0.5, "element_glow": 0.4, "background_dim": 0.3}
    ),
    PresetInfo(
        key="preset_dance_floor",
        name="Dance Floor",
        description="Club lights and movement",
        category="theme",
        explanation="You're in the middle of the dance floor. Lights spin around you, strobes flash, and particles fly. Pure club energy.",
        effects={"strobe_flash": 0.6, "energy_trails": 0.8, "particle_burst": 0.7, "element_scale": 0.6, "neon_outline": 0.4}
    ),
]


def create_single_effect_toggles(effect_key: str) -> EffectToggles:
    """Create toggles with only one effect enabled at max intensity."""
    toggles = EffectToggles()
    
    # Disable all effects first
    for attr_name in [
        "element_glow", "element_scale", "neon_outline", "echo_trail",
        "particle_burst", "energy_trails", "light_flares",
        "glitch", "ripple_wave", "film_grain", "strobe_flash", "vignette_pulse",
        "background_dim"
    ]:
        setattr(toggles, attr_name, EffectToggle(enabled=False, intensity=0.0))
    
    # Enable only the target effect at max intensity
    setattr(toggles, effect_key, EffectToggle(enabled=True, intensity=INTENSITY))
    
    return toggles


def create_preset_toggles(effects_dict: dict) -> EffectToggles:
    """Create toggles from a preset's effects dictionary."""
    toggles = EffectToggles()
    
    # Disable all effects first
    for attr_name in [
        "element_glow", "element_scale", "neon_outline", "echo_trail",
        "particle_burst", "energy_trails", "light_flares",
        "glitch", "ripple_wave", "film_grain", "strobe_flash", "vignette_pulse",
        "background_dim"
    ]:
        setattr(toggles, attr_name, EffectToggle(enabled=False, intensity=0.0))
    
    # Enable effects from the preset with their specified intensities
    for effect_key, intensity in effects_dict.items():
        setattr(toggles, effect_key, EffectToggle(enabled=True, intensity=intensity))
    
    return toggles


def generate_demo_video(key: str, name: str, toggles: EffectToggles, audio_features, image_path: str, audio_path: str) -> str:
    """Generate a demo video with the given toggles configuration."""
    output_path = DEMOS_OUTPUT_DIR / f"{key}.mp4"
    
    print(f"  Generating {name}...")
    
    # Default image context (centered subject)
    image_context = ImageContext(
        bounds=SubjectBounds(x=0.2, y=0.2, w=0.6, h=0.6),
        colors=["#FFD700", "#FF6B35", "#4ECDC4", "#9B59B6"],
        mood="energetic"
    )
    
    # Calculate effect parameters
    effect_params = calculate_effect_parameters(audio_features, toggles, image_context)
    
    # Render settings
    render_settings = RenderSettings(
        aspect_ratio=ASPECT_RATIO,
        fps=FPS,
        quality="medium",
        duration=DURATION,
        preview=True  # Use preview quality for faster generation
    )
    
    # Progress callback
    def progress_callback(progress: float):
        bar_length = 30
        filled = int(bar_length * progress)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"\r  [{bar}] {int(progress * 100)}%", end="", flush=True)
    
    # Render the video
    render_video(
        image_path=str(image_path),
        audio_path=str(audio_path),
        output_path=str(output_path),
        effect_params=effect_params,
        render_settings=render_settings,
        audio_start=AUDIO_START_TIME,
        progress_callback=progress_callback
    )
    
    print()  # New line after progress bar
    return str(output_path)


def generate_manifest(single_effects: list, presets: list) -> Dict[str, Any]:
    """Generate the manifest.json file."""
    manifest = {
        "version": "2.0",
        "audio_start_time": AUDIO_START_TIME,
        "duration": DURATION,
        "single_effects": [],
        "presets": []
    }
    
    for effect in single_effects:
        manifest["single_effects"].append({
            "key": effect.key,
            "name": effect.name,
            "description": effect.description,
            "category": effect.category,
            "explanation": effect.explanation,
            "video_url": f"/demos/{effect.key}.mp4"
        })
    
    for preset in presets:
        manifest["presets"].append({
            "key": preset.key,
            "name": preset.name,
            "description": preset.description,
            "category": preset.category,
            "explanation": preset.explanation,
            "effects": preset.effects,
            "video_url": f"/demos/{preset.key}.mp4"
        })
    
    return manifest


def main():
    print("=" * 60)
    print("Demo Video Generator")
    print("=" * 60)
    
    # Verify demo assets exist
    if not IMAGE_FILE.exists():
        print(f"ERROR: Demo image not found: {IMAGE_FILE}")
        sys.exit(1)
    if not AUDIO_FILE.exists():
        print(f"ERROR: Demo audio not found: {AUDIO_FILE}")
        sys.exit(1)
    
    total_videos = len(SINGLE_EFFECTS) + len(PRESETS)
    
    print(f"\nDemo assets:")
    print(f"  Image: {IMAGE_FILE.name}")
    print(f"  Audio: {AUDIO_FILE.name}")
    print(f"\nConfiguration:")
    print(f"  Audio start: {AUDIO_START_TIME}s (1:03)")
    print(f"  Duration: {DURATION}s")
    print(f"  Output: {DEMOS_OUTPUT_DIR}")
    print(f"\nVideos to generate:")
    print(f"  Single effects: {len(SINGLE_EFFECTS)}")
    print(f"  Curated presets: {len(PRESETS)}")
    print(f"  Total: {total_videos}")
    
    # Create output directory
    DEMOS_OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Analyze audio once (reused for all effects)
    print(f"\nAnalyzing audio...")
    audio_features = analyze_audio(
        str(AUDIO_FILE),
        start_time=AUDIO_START_TIME,
        duration=DURATION
    )
    print(f"  Tempo: {audio_features.tempo:.1f} BPM")
    print(f"  Beats detected: {len(audio_features.beat_times)}")
    
    current = 0
    
    # Generate videos for single effects
    print(f"\n{'='*60}")
    print("PART 1: Single Effects (13 videos)")
    print("=" * 60)
    
    for effect in SINGLE_EFFECTS:
        current += 1
        print(f"\n[{current}/{total_videos}] {effect.name} ({effect.category})")
        try:
            toggles = create_single_effect_toggles(effect.key)
            generate_demo_video(effect.key, effect.name, toggles, audio_features, IMAGE_FILE, AUDIO_FILE)
            print(f"  ✓ Saved: {effect.key}.mp4")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Generate videos for presets
    print(f"\n{'='*60}")
    print(f"PART 2: Curated Presets ({len(PRESETS)} videos)")
    print("=" * 60)
    
    for preset in PRESETS:
        current += 1
        effect_list = ", ".join(preset.effects.keys())
        print(f"\n[{current}/{total_videos}] {preset.name}")
        print(f"  Effects: {effect_list}")
        try:
            toggles = create_preset_toggles(preset.effects)
            generate_demo_video(preset.key, preset.name, toggles, audio_features, IMAGE_FILE, AUDIO_FILE)
            print(f"  ✓ Saved: {preset.key}.mp4")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Generate manifest
    print(f"\nGenerating manifest.json...")
    manifest = generate_manifest(SINGLE_EFFECTS, PRESETS)
    manifest_path = DEMOS_OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  ✓ Saved: manifest.json")
    
    print("\n" + "=" * 60)
    print("Demo generation complete!")
    print(f"Output directory: {DEMOS_OUTPUT_DIR}")
    print(f"Total videos: {total_videos}")
    print("=" * 60)


if __name__ == "__main__":
    main()

