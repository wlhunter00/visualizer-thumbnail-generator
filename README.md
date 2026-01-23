# Beat Visualizer

Create professional, beat-reactive music videos from your cover art and audio in seconds.

![Beat Visualizer](https://via.placeholder.com/800x400?text=Beat+Visualizer)

## Features

- **Simple 4-Step Flow**: Upload image → Upload audio → Adjust → Export
- **13 Customizable Effects**: Glow, scale pulse, neon outline, particles, glitch, and more
- **AI-Powered Analysis**: Automatic image analysis and effect suggestions
- **Visual Waveform Selection**: Drag to select exactly which part of your track to visualize
- **Effects Demo Page**: See all effects in action before creating your own
- **All Social Formats**: 9:16 (TikTok/Reels), 1:1 (Instagram), 16:9 (YouTube), 4:5 (Facebook)
- **Deep Linking**: Share direct links to specific effects (e.g., `#/demo/glitch`)

## Requirements

- Python 3.9+
- Node.js 18+
- FFmpeg

### Installing FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/yourusername/visualizer-thumbnail-generator.git
cd visualizer-thumbnail-generator
```

2. Run the start script:
```bash
chmod +x start.sh
./start.sh
```

3. Open http://localhost:5173 in your browser

4. (Optional) Generate effect demo videos:
```bash
cd backend
python generate_demos.py
```
This creates 30-second demo videos for each of the 13 effects, viewable at `#/demo`.

## Manual Setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## How It Works

### Audio Analysis
The backend uses [librosa](https://librosa.org/) to analyze your audio:
- Beat detection (kick, snare, hi-hat)
- Energy envelope (loudness over time)
- Onset detection (transients)
- Frequency band analysis (bass, mid, high)

### Effect Mapping
Your 3 slider settings control how audio features map to visual effects:

| Slider | Controls |
|--------|----------|
| Motion Intensity | How much the image moves/transforms |
| Beat Reactivity | How tightly effects sync to detected beats |
| Energy Level | Overall mood - calm to energetic |

### Available Effects (13 Total)

**Element Effects:**
- **Element Glow** - Pulsating light from your subject on beats
- **Scale Pulse** - Subject grows/shrinks on each beat
- **Neon Outline** - Glowing edge around subject (80s/cyberpunk aesthetic)
- **Echo Trail** - Ghostly afterimages creating motion blur

**Particle Effects:**
- **Particle Burst** - Particles explode outward on strong beats
- **Energy Trails** - Orbiting light trails synced to tempo
- **Light Flares** - Cinematic lens flares at bright spots

**Style Effects:**
- **Glitch** - RGB split, scan lines, slice displacement
- **Ripple Wave** - Circular distortion waves on beats
- **Film Grain** - Vintage film/VHS texture
- **Strobe Flash** - White flashes on strongest beats
- **Vignette Pulse** - Dark edges pulse with rhythm

**Background:**
- **Background Dim** - Darken/blur background for depth separation

View all effects in action at `#/demo` or visit the [Effects Demo](#effects-demo) section.

## Effects Demo

The app includes a demo page showcasing all 13 effects at maximum intensity. To generate the demo videos:

```bash
cd backend
python generate_demos.py
```

This will:
- Generate 13 videos (one per effect) at 100% intensity
- Use the demo assets from `demo-assets/` folder
- Start audio at 1:03 for a more interesting section
- Output to `backend/demos/` (gitignored)
- Take approximately 5-10 minutes depending on hardware

Once generated, visit `http://localhost:5173/#/demo` to view all effects.

**Deep linking:** You can link directly to a specific effect:
- `#/demo/glitch` - Glitch effect
- `#/demo/particle_burst` - Particle burst effect
- `#/demo/neon_outline` - Neon outline effect

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/session/create` | POST | Create new session |
| `/upload/image/{session_id}` | POST | Upload cover art |
| `/upload/audio/{session_id}` | POST | Upload audio file |
| `/audio/waveform/{session_id}` | GET | Get waveform data |
| `/analyze-image/{session_id}` | POST | AI image analysis |
| `/auto-suggest/{session_id}` | POST | Get AI effect suggestions |
| `/generate` | POST | Start video generation |
| `/generate/status/{session_id}` | GET | Check generation progress |
| `/export` | POST | Export final video |
| `/download/{session_id}` | GET | Download exported video |
| `/demos/manifest` | GET | Get demo videos manifest |

## Project Structure

```
visualizer-thumbnail-generator/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── audio_analysis.py    # librosa beat detection
│   ├── effect_engine.py     # Audio → visual mapping (13 effects)
│   ├── video_renderer.py    # FFmpeg video generation
│   ├── generate_demos.py    # Demo video generator script
│   ├── image_analysis.py    # AI image analysis
│   ├── demos/               # Generated demo videos (gitignored)
│   ├── outputs/             # Session outputs (cleaned on restart)
│   ├── uploads/             # Session uploads (cleaned on restart)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main application with routing
│   │   ├── DemoPage.tsx     # Effects demo page
│   │   ├── components/      # React components
│   │   ├── api.ts           # Backend API calls
│   │   └── types.ts         # TypeScript types
│   └── package.json
├── demo-assets/             # Demo image and audio for generating demos
├── start.sh                 # One-command startup
└── README.md
```

## License

MIT License - feel free to use for personal or commercial projects.

## Contributing

Contributions welcome! Please open an issue first to discuss what you'd like to change.

