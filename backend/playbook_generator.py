"""
Playbook Generator Module
Creates human-readable brand identity summaries based on the visual settings.
"""

from typing import Dict, Any, List
from effect_engine import EffectSettings, EffectParameters
from audio_analysis import AudioFeatures


def generate_playbook(
    settings: EffectSettings,
    audio_features: AudioFeatures,
    effect_params: EffectParameters
) -> Dict[str, Any]:
    """
    Generate a brand identity playbook based on the settings and audio.
    
    Returns a dictionary containing:
    - summary: A one-paragraph description of the visual identity
    - attributes: Key visual attributes
    - genre_fit: Suggested genres this style works well with
    - mood: Overall mood description
    - settings_used: The actual slider values used
    """
    
    intensity = settings.motion_intensity
    reactivity = settings.beat_reactivity
    energy = settings.energy_level
    tempo = audio_features.tempo
    
    # Determine visual style descriptors
    motion_descriptor = get_motion_descriptor(intensity)
    reactivity_descriptor = get_reactivity_descriptor(reactivity)
    energy_descriptor = get_energy_descriptor(energy)
    
    # Determine active effects
    active_effects = get_active_effects(effect_params)
    
    # Determine genre fit based on tempo and energy
    genres = get_genre_suggestions(tempo, energy, intensity)
    
    # Determine mood
    mood = get_mood_description(intensity, reactivity, energy)
    
    # Generate summary paragraph
    summary = generate_summary(
        motion_descriptor,
        reactivity_descriptor,
        energy_descriptor,
        active_effects,
        tempo
    )
    
    return {
        "summary": summary,
        "attributes": {
            "motion": motion_descriptor,
            "reactivity": reactivity_descriptor,
            "energy": energy_descriptor,
            "tempo": f"{int(tempo)} BPM"
        },
        "active_effects": active_effects,
        "genre_fit": genres,
        "mood": mood,
        "settings_used": {
            "motion_intensity": int(intensity * 100),
            "beat_reactivity": int(reactivity * 100),
            "energy_level": int(energy * 100)
        }
    }


def get_motion_descriptor(intensity: float) -> str:
    """Get a human-readable descriptor for motion intensity."""
    if intensity < 0.2:
        return "minimal"
    elif intensity < 0.4:
        return "subtle"
    elif intensity < 0.6:
        return "moderate"
    elif intensity < 0.8:
        return "dynamic"
    else:
        return "intense"


def get_reactivity_descriptor(reactivity: float) -> str:
    """Get a human-readable descriptor for beat reactivity."""
    if reactivity < 0.2:
        return "flowing"
    elif reactivity < 0.4:
        return "loosely synced"
    elif reactivity < 0.6:
        return "rhythmic"
    elif reactivity < 0.8:
        return "tightly synced"
    else:
        return "punch-reactive"


def get_energy_descriptor(energy: float) -> str:
    """Get a human-readable descriptor for energy level."""
    if energy < 0.2:
        return "calm"
    elif energy < 0.4:
        return "relaxed"
    elif energy < 0.6:
        return "balanced"
    elif energy < 0.8:
        return "energetic"
    else:
        return "high-energy"


def get_active_effects(effect_params: EffectParameters) -> List[str]:
    """Get list of active effects in human-readable form."""
    effects = []
    
    if effect_params.zoom_pulse.enabled:
        effects.append("breathing zoom")
    
    if effect_params.shake.enabled:
        effects.append("beat shake")
    
    if effect_params.blur_focus.enabled:
        effects.append("focus shifts")
    
    if effect_params.color_shift.enabled:
        effects.append("color warmth")
    
    if effect_params.particles.enabled:
        particle_type = effect_params.particles.particle_type
        effects.append(f"{particle_type} particles")
    
    if effect_params.geometric.enabled:
        shape_type = effect_params.geometric.shape_type
        effects.append(f"geometric {shape_type}")
    
    if effect_params.glitch.enabled:
        effects.append("glitch accents")
    
    return effects


def get_genre_suggestions(tempo: float, energy: float, intensity: float) -> List[str]:
    """Suggest genres that fit this visual style."""
    genres = []
    
    # Tempo-based suggestions
    if tempo < 100:
        genres.extend(["downtempo", "ambient", "lo-fi"])
    elif tempo < 120:
        genres.extend(["deep house", "chill", "R&B"])
    elif tempo < 135:
        genres.extend(["house", "tech house", "melodic techno"])
    elif tempo < 150:
        genres.extend(["techno", "trance", "EDM"])
    else:
        genres.extend(["drum & bass", "hardcore", "jungle"])
    
    # Energy-based filtering
    if energy < 0.3:
        genres = [g for g in genres if g in ["ambient", "lo-fi", "chill", "downtempo", "deep house"]]
        if not genres:
            genres = ["ambient", "lo-fi", "chill"]
    elif energy > 0.7:
        genres = [g for g in genres if g not in ["ambient", "lo-fi", "chill", "downtempo"]]
        if not genres:
            genres = ["EDM", "techno", "house"]
    
    # Intensity-based additions
    if intensity < 0.3:
        if "minimal" not in genres:
            genres.insert(0, "minimal")
    
    return genres[:4]  # Return top 4


def get_mood_description(intensity: float, reactivity: float, energy: float) -> str:
    """Generate a mood description."""
    
    # Calculate overall vibe
    vibe_score = (intensity + energy) / 2
    
    if vibe_score < 0.3:
        base_mood = "contemplative and serene"
    elif vibe_score < 0.5:
        base_mood = "smooth and inviting"
    elif vibe_score < 0.7:
        base_mood = "engaging and dynamic"
    else:
        base_mood = "powerful and electrifying"
    
    # Add reactivity modifier
    if reactivity > 0.6:
        base_mood += ", with strong rhythmic presence"
    elif reactivity < 0.3:
        base_mood += ", with an organic flow"
    
    return base_mood


def generate_summary(
    motion: str,
    reactivity: str,
    energy: str,
    effects: List[str],
    tempo: float
) -> str:
    """Generate a one-paragraph brand identity summary."""
    
    # Format effects list
    if len(effects) == 0:
        effects_str = "subtle visual movement"
    elif len(effects) == 1:
        effects_str = effects[0]
    elif len(effects) == 2:
        effects_str = f"{effects[0]} and {effects[1]}"
    else:
        effects_str = f"{', '.join(effects[:-1])}, and {effects[-1]}"
    
    # Build summary
    summary = f"Your visual identity features {motion} motion with {reactivity} beat response, "
    summary += f"creating a {energy} atmosphere. "
    summary += f"The video showcases {effects_str}, "
    summary += f"designed to complement music around {int(tempo)} BPM. "
    
    # Add recommendation
    if energy in ["calm", "relaxed"]:
        summary += "This style keeps your artwork as the focal point while adding tasteful movement that enhances without distracting."
    elif energy in ["energetic", "high-energy"]:
        summary += "This style brings energy and excitement while keeping your artwork recognizable and centered."
    else:
        summary += "This balanced approach creates engaging visuals that work across a variety of contexts."
    
    return summary


def playbook_to_preset(playbook: Dict[str, Any], name: str = "Custom") -> Dict[str, Any]:
    """Convert a playbook to a reusable preset format."""
    return {
        "name": name,
        "version": "1.0",
        "settings": playbook["settings_used"],
        "description": playbook["summary"],
        "mood": playbook["mood"],
        "genres": playbook["genre_fit"]
    }

