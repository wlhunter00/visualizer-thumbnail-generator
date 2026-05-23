"""
Transform Presets Module
Contains predefined prompts for AI-powered image transformation.
"""

from dataclasses import dataclass
from typing import Dict, List

@dataclass
class TransformPreset:
    """A preset transformation prompt."""
    key: str
    name: str
    description: str
    prompt: str
    thumbnail_color: str  # For UI display


# HuntingSzn Teal - Original v6.0
HUNTINGSZN_TEAL_PROMPT = """Create a 'HuntingSzn Re-Colour (v6.0)' version of the provided album cover. Do not add, remove, or crop any original shapes—only recolor and layer effects. Follow these exact steps:

1. Canvas & Base Texture  
   • Use the full original 1:1 artwork; preserve its entire frame.  
   • Behind it, fill a new layer with #0A0010 (deep navy-black).  
   • Overlay very fine noise (~10% opacity) on the entire canvas so the black never looks empty.  
   • Apply a dark-teal vignette (#002532 @ 20% opacity) around the outer 10% to softly frame the subject.

2. Teal/Blue Color Mapping  
   • Recolor every pixel into three teal values:  
     – Shadows → #002532 (almost-black teal)  
     – Midtones → #005768 (rich deep teal)  
     – Highlights → #33C2E0 (bright aqua)  
   • Boost overall contrast so darkest areas read nearly black and brightest aqua highlights glow sharply. Ensure all original details (faces, textures, objects) remain fully recognizable.

3. Pronounced Crystalline Accents  
   • Wherever the original has glossy, metallic, or bright highlights (e.g., reflections on skin, stickers, metal), overlay a crystalline "ice" pattern in pale cyan (#A0F4FE @ 12% opacity).  
     – Cracks and ice veins should follow existing highlights only and never create new shapes.  
     – Keep all crystalline accents strictly in the teal/aqua range—no pink or other colors.

4. Enriched Background Layers  
   a. **Topographic Contours**  
      • Draw organic contour lines in #004A60 (dark teal) at 18–20% opacity across the entire background behind the subject.  
      • Lines should weave fluidly, giving layered depth—especially behind darker areas like hair or shadowed regions—without overwhelming the subject.  
   b. **Glitch Streaks**  
      • Add very faint, horizontal glitch streaks (#7D00FF @ 0.5% opacity), placing only one short streak near each side edge.  
      • Taper these streaks so they diminish toward the center, never covering the main focal points.  
   c. **Film Grain & Smoke**  
      • Combine a fine film grain (3–5% opacity) with a slightly heavier film grain layer (5–7% opacity) so overall grain ≈6% opacity—uniform and never blotchy.  
      • Overlay a translucent smoke/mist layer (dark teal #005768 @ 7% opacity) drifting behind the subject's head and upper shoulders to fill negative space without drawing attention.

5. Minimized Waveform Underlay  
   • Place **two short waveform segments** in bright aqua (#33C2E0 @ 20% opacity), each spanning ~20% of the canvas width.  
   • Position one on the left and one on the right of the subject, behind neck or existing gaps—only visible through small breaks in the artwork.  
   • Keep each waveform line ~1.5 px thick and symmetrical. If the background has no gaps, skip both segments entirely.

6. Balanced Glow & Outline  
   • Around the subject's brightest edges (e.g., sticker borders, lips, prominent contours), draw a **2 px outline** in #33C2E0 @ 10% opacity.  
   • Apply a **6 px Gaussian blur** to that outline to create a soft neon halo—visible but contained.  
   • Add a narrow outer glow around the frame's edges (outer 15%) in #005768 @ 8% opacity, ~5 px spread, to prevent any corner from feeling too empty.

7. Subtle Scan Lines  
   • Overlay a very faint horizontal scan-line pattern (#002532 @ 3% opacity) across the entire image.  
   • Ensure these lines never obscure important details—only a slight "CRT flicker" effect in negative spaces.

8. Typography (Single Bottom Line)  
   • Font: Montserrat ExtraBold (vector text, not AI-drawn).  
   • Color: #33C2E0 (bright aqua).  
   • Render only: "HUNTINGSZN FLIP" (all caps).  
   • Placement: Centered horizontally, 8% up from the bottom edge.  
   • Size: Scale text so it spans ~30–35% of canvas width, tracking = 0.  
   • Contrast Aid: If text overlaps brighter teal areas, add a 1 px dark-teal outline (#002532) or a 2 px drop shadow (#002532 @ 30% opacity) to ensure crisp legibility.

9. No Additional Logos or Text  
   • Do **not** add any other text (artist name, song title) or any logo badges/watermarks. Only "HUNTINGSZN FLIP" should appear.  
   • Preserve any original text from the source artwork, recolored by the teal mapping. Do not remove or modify it.

**Final Result:** A dark, textured, immersive cover that:
- Preserves the original artwork in full, recolored in a three-level teal palette.
- Layers rich crystalline highlights, deeper contour lines, subtle glitch, uniform film grain, and smoky mist for visual depth.
- Features only one line of bold, bright-aqua text at the bottom.

This will read as a professional HuntingSzn release—moody, icy, and meticulously crafted."""


# HuntingSzn Purple - Variant with purple/magenta color scheme
HUNTINGSZN_PURPLE_PROMPT = """Create a 'HuntingSzn Re-Colour (Purple Edition)' version of the provided album cover. Do not add, remove, or crop any original shapes—only recolor and layer effects. Follow these exact steps:

1. Canvas & Base Texture  
   • Use the full original 1:1 artwork; preserve its entire frame.  
   • Behind it, fill a new layer with #0D0015 (deep purple-black).  
   • Overlay very fine noise (~10% opacity) on the entire canvas so the black never looks empty.  
   • Apply a dark-purple vignette (#1A0030 @ 20% opacity) around the outer 10% to softly frame the subject.

2. Purple/Magenta Color Mapping  
   • Recolor every pixel into three purple values:  
     – Shadows → #1A0030 (almost-black purple)  
     – Midtones → #4A0080 (rich deep purple)  
     – Highlights → #E040FB (bright magenta)  
   • Boost overall contrast so darkest areas read nearly black and brightest magenta highlights glow sharply. Ensure all original details (faces, textures, objects) remain fully recognizable.

3. Pronounced Crystalline Accents  
   • Wherever the original has glossy, metallic, or bright highlights (e.g., reflections on skin, stickers, metal), overlay a crystalline pattern in pale pink (#FFB0FF @ 12% opacity).  
     – Cracks and veins should follow existing highlights only and never create new shapes.  
     – Keep all crystalline accents strictly in the purple/magenta range.

4. Enriched Background Layers  
   a. **Topographic Contours**  
      • Draw organic contour lines in #3D0066 (dark purple) at 18–20% opacity across the entire background behind the subject.  
   b. **Glitch Streaks**  
      • Add very faint, horizontal glitch streaks (#00FFFF @ 0.5% opacity), placing only one short streak near each side edge.  
   c. **Film Grain & Smoke**  
      • Combine a fine film grain (3–5% opacity) with a slightly heavier film grain layer (5–7% opacity) so overall grain ≈6% opacity.  
      • Overlay a translucent smoke/mist layer (dark purple #4A0080 @ 7% opacity) drifting behind the subject.

5. Balanced Glow & Outline  
   • Around the subject's brightest edges, draw a **2 px outline** in #E040FB @ 10% opacity.  
   • Apply a **6 px Gaussian blur** to that outline to create a soft neon halo.  
   • Add a narrow outer glow around the frame's edges in #4A0080 @ 8% opacity.

6. Subtle Scan Lines  
   • Overlay a very faint horizontal scan-line pattern (#1A0030 @ 3% opacity) across the entire image.

7. Typography (Single Bottom Line)  
   • Font: Montserrat ExtraBold.  
   • Color: #E040FB (bright magenta).  
   • Render only: "HUNTINGSZN FLIP" (all caps).  
   • Placement: Centered horizontally, 8% up from the bottom edge.  
   • Size: Scale text so it spans ~30–35% of canvas width.

8. No Additional Logos or Text  
   • Preserve any original text from the source artwork, recolored by the purple mapping.

**Final Result:** A dark, immersive cover recolored in a three-level purple/magenta palette with crystalline highlights and neon glow."""


# Minimal Clean - Simple style with no text overlay
MINIMAL_CLEAN_PROMPT = """Transform the provided album cover into a clean, minimal aesthetic version. Do not add, remove, or crop any original shapes—only apply color grading and subtle effects:

1. Color Grading
   • Apply a desaturated, moody color grade
   • Shadows: Deep charcoal (#1A1A1A)
   • Midtones: Soft gray-blue (#4A5568)
   • Highlights: Clean white with slight warmth (#F7FAFC)
   • Reduce overall saturation by 40%
   • Increase contrast slightly for definition

2. Subtle Effects
   • Add very fine film grain (~3% opacity) for texture
   • Apply soft vignette around edges (15% opacity)
   • Gentle sharpening on subject edges

3. No Text Overlay
   • Do NOT add any text, logos, or watermarks
   • Preserve any original text from the source, color-graded to match

4. Atmosphere
   • Add subtle ambient light bloom on bright areas
   • Soft fade on darkest shadows

**Final Result:** A clean, professional-looking cover with moody color grading, subtle texture, and no added text—perfect for versatile use."""


# All presets
PRESETS: Dict[str, TransformPreset] = {
    "huntingszn_teal": TransformPreset(
        key="huntingszn_teal",
        name="HuntingSzn Teal",
        description="Dark, icy teal palette with crystalline highlights, glitch effects, and 'HUNTINGSZN FLIP' text overlay",
        prompt=HUNTINGSZN_TEAL_PROMPT,
        thumbnail_color="#33C2E0"
    ),
    "huntingszn_purple": TransformPreset(
        key="huntingszn_purple",
        name="HuntingSzn Purple",
        description="Rich purple/magenta variant with neon glow and 'HUNTINGSZN FLIP' text overlay",
        prompt=HUNTINGSZN_PURPLE_PROMPT,
        thumbnail_color="#E040FB"
    ),
    "minimal_clean": TransformPreset(
        key="minimal_clean",
        name="Minimal Clean",
        description="Desaturated, moody color grade with subtle film grain—no text overlay",
        prompt=MINIMAL_CLEAN_PROMPT,
        thumbnail_color="#4A5568"
    ),
}


def get_preset(key: str) -> TransformPreset:
    """Get a preset by key."""
    if key not in PRESETS:
        raise ValueError(f"Unknown preset: {key}")
    return PRESETS[key]


def get_all_presets() -> List[Dict]:
    """Get all presets as a list of dicts for API response."""
    return [
        {
            "key": preset.key,
            "name": preset.name,
            "description": preset.description,
            "thumbnail_color": preset.thumbnail_color,
        }
        for preset in PRESETS.values()
    ]

