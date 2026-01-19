# Beat Visualizer

Create professional, beat-reactive music videos from your cover art and audio in seconds.

![Beat Visualizer](https://via.placeholder.com/800x400?text=Beat+Visualizer)

## Features

- **Simple 4-Step Flow**: Upload image → Upload audio → Adjust → Export
- **Beat-Reactive Effects**: Zoom pulse, shake, blur, color shifts, particles, geometric overlays, glitch
- **Visual Waveform Selection**: Drag to select exactly which part of your track to visualize
- **3 High-Level Controls**: Motion Intensity, Beat Reactivity, Energy Level
- **All Social Formats**: 9:16 (TikTok/Reels), 1:1 (Instagram), 16:9 (YouTube), 4:5 (Facebook)
- **Brand Playbook**: Get a summary of your visual identity to maintain consistency

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

### Available Effects

1. **Zoom Pulse** - Subtle in/out breathing synced to beats
2. **Shake** - Quick vibration on strong transients
3. **Blur/Focus** - Depth-of-field shifts following energy
4. **Color Shift** - Warmth and brightness changes
5. **Particles** - Floating dust, sparkles, or bokeh
6. **Geometric** - Lines, circles, or grid overlays on beats
7. **Glitch** - Chromatic aberration and slice displacement

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/session/create` | POST | Create new session |
| `/upload/image/{session_id}` | POST | Upload cover art |
| `/upload/audio/{session_id}` | POST | Upload audio file |
| `/audio/waveform/{session_id}` | GET | Get waveform data |
| `/generate` | POST | Start video generation |
| `/generate/status/{session_id}` | GET | Check generation progress |
| `/export` | POST | Export final video |
| `/download/{session_id}` | GET | Download exported video |

## Project Structure

```
visualizer-thumbnail-generator/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── audio_analysis.py    # librosa beat detection
│   ├── effect_engine.py     # Audio → visual mapping
│   ├── video_renderer.py    # FFmpeg video generation
│   ├── playbook_generator.py # Brand identity summary
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main application
│   │   ├── components/      # React components
│   │   ├── api.ts           # Backend API calls
│   │   └── types.ts         # TypeScript types
│   └── package.json
├── start.sh                 # One-command startup
└── README.md
```

## License

MIT License - feel free to use for personal or commercial projects.

## Contributing

Contributions welcome! Please open an issue first to discuss what you'd like to change.

