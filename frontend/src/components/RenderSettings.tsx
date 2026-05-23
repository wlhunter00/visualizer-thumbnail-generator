import { Monitor, Maximize, Film, ChevronDown } from 'lucide-react';
import { ASPECT_RATIOS, RENDER_RESOLUTIONS } from '../types';

interface RenderSettingsProps {
  aspectRatio: string;
  resolution: string;
  onAspectRatioChange: (value: string) => void;
  onResolutionChange: (value: string) => void;
  compact?: boolean;
}

export default function RenderSettings({
  aspectRatio,
  resolution,
  onAspectRatioChange,
  onResolutionChange,
  compact = false,
}: RenderSettingsProps) {
  const selectedAspect = ASPECT_RATIOS.find(r => r.value === aspectRatio);
  const selectedResolution = RENDER_RESOLUTIONS.find(r => r.value === resolution);

  // Calculate approximate output dimensions for display
  const getDimensions = () => {
    const baseWidth = aspectRatio === '16:9' ? 1920 : 1080;
    const baseHeight = aspectRatio === '9:16' ? 1920 : 
                       aspectRatio === '1:1' ? 1080 : 
                       aspectRatio === '4:5' ? 1350 : 1080;
    
    const scale = selectedResolution?.scale || 1.0;
    return {
      width: Math.round(baseWidth * scale),
      height: Math.round(baseHeight * scale),
    };
  };

  const dims = getDimensions();

  if (compact) {
    return (
      <div className="bg-white rounded-2xl border border-surface-200 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Film className="w-4 h-4 text-accent" />
          <span className="text-sm font-medium text-surface-700">Output Settings</span>
        </div>

        <div className="space-y-4">
          {/* Resolution Dropdown */}
          <div>
            <label className="block text-xs text-surface-500 mb-2">Resolution</label>
            <div className="relative">
              <select
                value={resolution}
                onChange={(e) => onResolutionChange(e.target.value)}
                className="w-full appearance-none bg-surface-100 border border-surface-200 rounded-xl px-4 py-3 pr-10 text-sm font-medium text-surface-700 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent cursor-pointer"
              >
                {RENDER_RESOLUTIONS.map((res) => (
                  <option key={res.value} value={res.value}>
                    {res.label} — {res.description}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400 pointer-events-none" />
            </div>
          </div>

          {/* Aspect Ratio Pills */}
          <div>
            <label className="block text-xs text-surface-500 mb-2">Aspect Ratio</label>
            <div className="grid grid-cols-2 gap-2">
              {ASPECT_RATIOS.map((ratio) => (
                <button
                  key={ratio.value}
                  onClick={() => onAspectRatioChange(ratio.value)}
                  className={`px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    aspectRatio === ratio.value
                      ? 'bg-accent text-white'
                      : 'bg-surface-100 text-surface-600 hover:bg-surface-200'
                  }`}
                >
                  {ratio.value}
                </button>
              ))}
            </div>
          </div>

          {/* Dimensions Display */}
          <div className="pt-2 border-t border-surface-100">
            <div className="flex items-center justify-between text-xs">
              <span className="text-surface-500">Output Size</span>
              <span className="font-mono text-surface-700 bg-surface-100 px-2 py-1 rounded">
                {dims.width} × {dims.height}
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Full layout (for Step 3 style)
  return (
    <div className="bg-white rounded-2xl border border-surface-200 p-4 space-y-4">
      <div className="flex items-center gap-2">
        <Monitor className="w-4 h-4 text-accent" />
        <span className="text-sm font-medium text-surface-700">Render Settings</span>
      </div>

      {/* Aspect Ratio */}
      <div>
        <span className="text-xs text-surface-500 block mb-2">Aspect Ratio</span>
        <div className="grid grid-cols-2 gap-2">
          {ASPECT_RATIOS.map((ratio) => (
            <button
              key={ratio.value}
              onClick={() => onAspectRatioChange(ratio.value)}
              className={`p-3 rounded-xl text-left transition-all ${
                aspectRatio === ratio.value
                  ? 'bg-accent text-white'
                  : 'bg-surface-100 hover:bg-surface-200 text-surface-700'
              }`}
            >
              <div className="text-sm font-medium">{ratio.label}</div>
              <div className={`text-xs ${
                aspectRatio === ratio.value ? 'text-white/70' : 'text-surface-500'
              }`}>
                {ratio.description}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Resolution */}
      <div>
        <span className="text-xs text-surface-500 block mb-2">Export Resolution</span>
        <div className="space-y-2">
          {RENDER_RESOLUTIONS.map((res) => (
            <button
              key={res.value}
              onClick={() => onResolutionChange(res.value)}
              className={`w-full p-3 rounded-xl text-left transition-all flex items-center justify-between ${
                resolution === res.value
                  ? 'bg-accent text-white'
                  : 'bg-surface-100 hover:bg-surface-200 text-surface-700'
              }`}
            >
              <div>
                <div className="text-sm font-medium">{res.label}</div>
                <div className={`text-xs ${
                  resolution === res.value ? 'text-white/70' : 'text-surface-500'
                }`}>
                  {res.description}
                </div>
              </div>
              <Maximize className={`w-4 h-4 ${
                resolution === res.value ? 'text-white/70' : 'text-surface-400'
              }`} />
            </button>
          ))}
        </div>
      </div>

      {/* Output Dimensions */}
      <div className="pt-3 border-t border-surface-100">
        <div className="flex items-center justify-between">
          <span className="text-xs text-surface-500">Final Output</span>
          <span className="text-sm font-mono font-medium text-surface-700">
            {dims.width} × {dims.height}px
          </span>
        </div>
      </div>
    </div>
  );
}

