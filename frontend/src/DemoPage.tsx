import { useState, useEffect, useRef, useCallback } from 'react';
import { getDemoManifest, getDemoVideoUrl, DemoEffect, DemoPreset, DemoManifest } from './api';
import { 
  Sparkles, 
  Target, 
  Film, 
  Zap, 
  ArrowLeft, 
  Link2, 
  Check,
  AlertCircle,
  Loader2,
  Play,
  Layers,
  Music,
  Smartphone,
  Palette,
  Gauge
} from 'lucide-react';

interface DemoPageProps {
  initialEffect?: string;
  onNavigateHome: () => void;
}

// Single effect category styling
const effectCategoryIcons: Record<string, React.ReactNode> = {
  element: <Target className="w-4 h-4" />,
  particle: <Sparkles className="w-4 h-4" />,
  style: <Film className="w-4 h-4" />,
  background: <Zap className="w-4 h-4" />,
};

const effectCategoryColors: Record<string, string> = {
  element: 'bg-blue-100 text-blue-700 border-blue-200',
  particle: 'bg-amber-100 text-amber-700 border-amber-200',
  style: 'bg-purple-100 text-purple-700 border-purple-200',
  background: 'bg-emerald-100 text-emerald-700 border-emerald-200',
};

const effectCategoryNames: Record<string, string> = {
  element: 'Element Effects',
  particle: 'Particle Effects',
  style: 'Style Effects',
  background: 'Background Effects',
};

// Preset category styling
const presetCategoryIcons: Record<string, React.ReactNode> = {
  mood: <Palette className="w-4 h-4" />,
  genre: <Music className="w-4 h-4" />,
  combo: <Layers className="w-4 h-4" />,
  intensity: <Gauge className="w-4 h-4" />,
  platform: <Smartphone className="w-4 h-4" />,
  theme: <Sparkles className="w-4 h-4" />,
};

const presetCategoryColors: Record<string, string> = {
  mood: 'bg-pink-100 text-pink-700 border-pink-200',
  genre: 'bg-indigo-100 text-indigo-700 border-indigo-200',
  combo: 'bg-orange-100 text-orange-700 border-orange-200',
  intensity: 'bg-red-100 text-red-700 border-red-200',
  platform: 'bg-cyan-100 text-cyan-700 border-cyan-200',
  theme: 'bg-violet-100 text-violet-700 border-violet-200',
};

const presetCategoryNames: Record<string, string> = {
  mood: 'Mood & Vibe',
  genre: 'Genre-Specific',
  combo: 'Effect Combos',
  intensity: 'Intensity Levels',
  platform: 'Platform-Optimized',
  theme: 'Themed Styles',
};

function VideoCard({ 
  id,
  name,
  description,
  category,
  categoryIcon,
  categoryColor,
  explanation,
  videoKey,
  badge,
  effectsList,
  isHighlighted,
  onCopyLink 
}: { 
  id: string;
  name: string;
  description: string;
  category: string;
  categoryIcon: React.ReactNode;
  categoryColor: string;
  explanation: string;
  videoKey: string;
  badge?: string;
  effectsList?: Record<string, number>;
  isHighlighted: boolean;
  onCopyLink: (key: string) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [copied, setCopied] = useState(false);

  // Update progress bar
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      if (video.duration) {
        setProgress((video.currentTime / video.duration) * 100);
      }
    };

    const handleLoadedMetadata = () => {
      setDuration(video.duration);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setProgress(0);
    };

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('ended', handleEnded);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('ended', handleEnded);
    };
  }, []);

  const handleCopyLink = () => {
    onCopyLink(id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleVideoClick = () => {
    if (videoRef.current) {
      if (videoRef.current.paused) {
        // Pause all other videos first
        document.querySelectorAll('video').forEach(v => {
          if (v !== videoRef.current) {
            v.pause();
            v.currentTime = 0;
          }
        });
        
        videoRef.current.play().catch(err => {
          console.error('Play failed:', err);
        });
        setIsPlaying(true);
      } else {
        videoRef.current.pause();
        setIsPlaying(false);
      }
    }
  };

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (videoRef.current && duration) {
      const rect = e.currentTarget.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const percentage = clickX / rect.width;
      videoRef.current.currentTime = percentage * duration;
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div
      id={`effect-${id}`}
      className={`bg-white rounded-2xl border overflow-hidden transition-all duration-500 ${
        isHighlighted 
          ? 'border-violet-400 ring-4 ring-violet-100 shadow-xl scale-[1.02]' 
          : 'border-surface-200 hover:border-surface-300 hover:shadow-lg'
      }`}
    >
      {/* Video Preview */}
      <div className="relative aspect-[9/16] bg-surface-900 cursor-pointer group">
        <video
          ref={videoRef}
          src={getDemoVideoUrl(videoKey)}
          className="w-full h-full object-cover"
          playsInline
          preload="metadata"
          onClick={handleVideoClick}
        />
        
        {/* Play overlay */}
        {!isPlaying && (
          <div 
            className="absolute inset-0 flex items-center justify-center bg-black/30 hover:bg-black/20 transition-colors"
            onClick={handleVideoClick}
          >
            <div className="w-16 h-16 rounded-full bg-white/90 flex items-center justify-center shadow-lg hover:scale-110 transition-transform">
              <Play className="w-8 h-8 text-surface-800 ml-1" />
            </div>
          </div>
        )}

        {/* Badge */}
        {badge && (
          <div className="absolute top-3 right-3 px-2 py-1 bg-black/60 backdrop-blur-sm rounded-full text-xs font-medium text-white">
            {badge}
          </div>
        )}

        {/* Progress bar and time */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3">
          {/* Time display */}
          <div className="flex justify-between text-xs text-white/80 mb-1">
            <span>{formatTime((progress / 100) * duration)}</span>
            <span>{formatTime(duration)}</span>
          </div>
          
          {/* Clickable progress bar */}
          <div 
            className="h-1.5 bg-white/30 rounded-full cursor-pointer overflow-hidden"
            onClick={handleProgressClick}
          >
            <div 
              className="h-full bg-violet-500 rounded-full transition-all duration-100"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div>
            <h3 className="font-display font-bold text-surface-900 text-lg">
              {name}
            </h3>
            <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${categoryColor}`}>
              {categoryIcon}
              {category.charAt(0).toUpperCase() + category.slice(1)}
            </span>
          </div>
          
          {/* Copy link button */}
          <button
            onClick={handleCopyLink}
            className="p-2 rounded-lg hover:bg-surface-100 transition-colors text-surface-500 hover:text-surface-700"
            title="Copy link to this demo"
          >
            {copied ? (
              <Check className="w-4 h-4 text-green-600" />
            ) : (
              <Link2 className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Description */}
        <p className="text-sm text-surface-500 mb-3">
          {description}
        </p>

        {/* Effects list for presets */}
        {effectsList && (
          <div className="flex flex-wrap gap-1 mb-3">
            {Object.entries(effectsList).map(([effect, intensity]) => (
              <span 
                key={effect}
                className="text-xs px-2 py-0.5 bg-surface-100 text-surface-600 rounded-full"
                title={`${Math.round(intensity * 100)}% intensity`}
              >
                {effect.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}

        {/* Explanation */}
        <div className="bg-surface-50 rounded-xl p-3">
          <p className="text-sm text-surface-700 leading-relaxed">
            {explanation}
          </p>
        </div>
      </div>
    </div>
  );
}

export default function DemoPage({ initialEffect, onNavigateHome }: DemoPageProps) {
  const [manifest, setManifest] = useState<DemoManifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [highlightedEffect, setHighlightedEffect] = useState<string | null>(initialEffect || null);
  const [activeTab, setActiveTab] = useState<'presets' | 'effects'>('effects'); // Default to effects until presets exist

  // Load manifest
  useEffect(() => {
    getDemoManifest()
      .then(data => {
        setManifest(data);
        setLoading(false);
        
        // Auto-select tab based on initial effect or available content
        if (initialEffect) {
          const isPreset = data.presets?.some(p => p.key === initialEffect);
          setActiveTab(isPreset ? 'presets' : 'effects');
        } else if (data.presets?.length > 0) {
          // Default to presets tab if presets exist
          setActiveTab('presets');
        }
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [initialEffect]);

  // Scroll to effect on load or when initialEffect changes
  useEffect(() => {
    if (initialEffect && manifest) {
      const element = document.getElementById(`effect-${initialEffect}`);
      if (element) {
        setTimeout(() => {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
          setHighlightedEffect(initialEffect);
          
          // Remove highlight after animation
          setTimeout(() => {
            setHighlightedEffect(null);
          }, 2000);
        }, 100);
      }
    }
  }, [initialEffect, manifest, activeTab]);

  // Handle copy link
  const handleCopyLink = useCallback((effectKey: string) => {
    const url = `${window.location.origin}${window.location.pathname}#/demo/${effectKey}`;
    navigator.clipboard.writeText(url);
    
    // Update URL without reload
    window.history.replaceState(null, '', `#/demo/${effectKey}`);
  }, []);

  // Group single effects by category
  const effectsByCategory = manifest?.single_effects?.reduce((acc, effect) => {
    if (!acc[effect.category]) {
      acc[effect.category] = [];
    }
    acc[effect.category].push(effect);
    return acc;
  }, {} as Record<string, DemoEffect[]>) || {};

  // Group presets by category
  const presetsByCategory = manifest?.presets?.reduce((acc, preset) => {
    if (!acc[preset.category]) {
      acc[preset.category] = [];
    }
    acc[preset.category].push(preset);
    return acc;
  }, {} as Record<string, DemoPreset[]>) || {};

  const effectCategoryOrder = ['element', 'particle', 'style', 'background'];
  const presetCategoryOrder = ['mood', 'genre', 'combo', 'intensity', 'platform', 'theme'];

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-violet-500 animate-spin mx-auto mb-4" />
          <p className="text-surface-600">Loading effect demos...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-surface-50 flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white rounded-2xl border border-surface-200 p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-amber-100 flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-amber-600" />
          </div>
          <h2 className="font-display text-xl font-bold text-surface-900 mb-2">
            Demo Videos Not Available
          </h2>
          <p className="text-surface-600 mb-6">
            {error}
          </p>
          <div className="bg-surface-50 rounded-xl p-4 text-left mb-6">
            <p className="text-sm text-surface-700 font-mono">
              cd backend<br />
              python generate_demos.py
            </p>
          </div>
          <button
            onClick={onNavigateHome}
            className="inline-flex items-center gap-2 px-4 py-2 bg-violet-500 text-white rounded-lg hover:bg-violet-600 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Beat Visualizer
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-50">
      {/* Header */}
      <header className="border-b border-surface-200 bg-white sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onNavigateHome}
              className="p-2 rounded-lg hover:bg-surface-100 transition-colors text-surface-600"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="font-display text-xl font-bold text-surface-900">Effects Demo</h1>
              <p className="text-sm text-surface-500">See all 13 effects in action</p>
            </div>
          </div>
          
          <button
            onClick={onNavigateHome}
            className="hidden sm:inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-violet-500 to-purple-600 text-white font-medium rounded-lg hover:from-violet-600 hover:to-purple-700 transition-all shadow-lg shadow-purple-500/20"
          >
            <Sparkles className="w-4 h-4" />
            Create Your Own
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <div className="bg-gradient-to-b from-violet-50 to-surface-50 border-b border-surface-200">
        <div className="max-w-7xl mx-auto px-6 py-12 text-center">
          <h2 className="font-display text-3xl sm:text-4xl font-bold text-surface-900 mb-4">
            Explore All Visual Effects
          </h2>
          <p className="text-lg text-surface-600 max-w-2xl mx-auto mb-8">
            Hover over any video to preview, or click to play. 
            Browse curated presets for instant inspiration, or explore individual effects.
          </p>
          
          {/* Tab Switcher - only show if we have presets */}
          {(manifest?.presets?.length ?? 0) > 0 && (
            <div className="inline-flex bg-white rounded-xl border border-surface-200 p-1 shadow-sm">
              <button
                onClick={() => setActiveTab('presets')}
                className={`px-6 py-2.5 rounded-lg font-medium transition-all ${
                  activeTab === 'presets'
                    ? 'bg-violet-500 text-white shadow-sm'
                    : 'text-surface-600 hover:text-surface-900 hover:bg-surface-50'
                }`}
              >
                <span className="flex items-center gap-2">
                  <Layers className="w-4 h-4" />
                  Curated Presets ({manifest?.presets?.length || 0})
                </span>
              </button>
              <button
                onClick={() => setActiveTab('effects')}
                className={`px-6 py-2.5 rounded-lg font-medium transition-all ${
                  activeTab === 'effects'
                    ? 'bg-violet-500 text-white shadow-sm'
                    : 'text-surface-600 hover:text-surface-900 hover:bg-surface-50'
                }`}
              >
                <span className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4" />
                  Single Effects ({manifest?.single_effects?.length || 0})
                </span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Presets Tab */}
        {activeTab === 'presets' && (
          <>
            {presetCategoryOrder.map(category => {
              const presets = presetsByCategory[category];
              if (!presets?.length) return null;

              return (
                <section key={category} className="mb-16">
                  {/* Category Header */}
                  <div className="flex items-center gap-3 mb-6">
                    <div className={`p-2 rounded-lg ${presetCategoryColors[category]}`}>
                      {presetCategoryIcons[category]}
                    </div>
                    <div>
                      <h2 className="font-display text-2xl font-bold text-surface-900">
                        {presetCategoryNames[category]}
                      </h2>
                      <p className="text-sm text-surface-500">
                        {presets.length} preset{presets.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                  </div>

                  {/* Presets Grid */}
                  <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {presets.map(preset => (
                      <VideoCard
                        key={preset.key}
                        id={preset.key}
                        name={preset.name}
                        description={preset.description}
                        category={preset.category}
                        categoryIcon={presetCategoryIcons[preset.category]}
                        categoryColor={presetCategoryColors[preset.category]}
                        explanation={preset.explanation}
                        videoKey={preset.key}
                        badge={`${Object.keys(preset.effects).length} effects`}
                        effectsList={preset.effects}
                        isHighlighted={highlightedEffect === preset.key}
                        onCopyLink={handleCopyLink}
                      />
                    ))}
                  </div>
                </section>
              );
            })}
          </>
        )}

        {/* Single Effects Tab */}
        {activeTab === 'effects' && (
          <>
            {effectCategoryOrder.map(category => {
              const effects = effectsByCategory[category];
              if (!effects?.length) return null;

              return (
                <section key={category} className="mb-16">
                  {/* Category Header */}
                  <div className="flex items-center gap-3 mb-6">
                    <div className={`p-2 rounded-lg ${effectCategoryColors[category]}`}>
                      {effectCategoryIcons[category]}
                    </div>
                    <div>
                      <h2 className="font-display text-2xl font-bold text-surface-900">
                        {effectCategoryNames[category]}
                      </h2>
                      <p className="text-sm text-surface-500">
                        {effects.length} effect{effects.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                  </div>

                  {/* Effects Grid */}
                  <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {effects.map(effect => (
                      <VideoCard
                        key={effect.key}
                        id={effect.key}
                        name={effect.name}
                        description={effect.description}
                        category={effect.category}
                        categoryIcon={effectCategoryIcons[effect.category]}
                        categoryColor={effectCategoryColors[effect.category]}
                        explanation={effect.explanation}
                        videoKey={effect.key}
                        badge="100% Intensity"
                        isHighlighted={highlightedEffect === effect.key}
                        onCopyLink={handleCopyLink}
                      />
                    ))}
                  </div>
                </section>
              );
            })}
          </>
        )}

        {/* CTA Section */}
        <div className="mt-16 bg-gradient-to-r from-violet-500 to-purple-600 rounded-3xl p-8 sm:p-12 text-center text-white">
          <h2 className="font-display text-2xl sm:text-3xl font-bold mb-4">
            Ready to Create Your Own?
          </h2>
          <p className="text-violet-100 mb-8 max-w-xl mx-auto">
            Upload your cover art and music, then mix and match these effects 
            to create stunning beat-reactive visualizations.
          </p>
          <button
            onClick={onNavigateHome}
            className="inline-flex items-center gap-2 px-8 py-4 bg-white text-violet-600 font-bold rounded-xl hover:bg-violet-50 transition-colors shadow-lg"
          >
            <Sparkles className="w-5 h-5" />
            Start Creating
          </button>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-surface-200 bg-white py-8">
        <div className="max-w-7xl mx-auto px-6 text-center text-sm text-surface-500">
          <p>
            All demo videos use the same source image and audio clip starting at 1:03 
            to showcase each effect in isolation at maximum intensity.
          </p>
        </div>
      </footer>
    </div>
  );
}

