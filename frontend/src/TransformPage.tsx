import { useState, useEffect, useCallback } from 'react';
import { 
  createSession, 
  uploadImage, 
  getTransformPresets, 
  transformImage, 
  getTransformStatus,
  getSessionImageUrl,
  TransformPreset
} from './api';
import { 
  Sparkles, 
  Upload, 
  Image as ImageIcon, 
  Loader2, 
  ArrowRight, 
  ChevronDown,
  Wand2,
  RefreshCw
} from 'lucide-react';

interface TransformPageProps {
  onNavigateToVideo: (sessionId: string) => void;
  onNavigateHome: () => void;
}

export default function TransformPage({ onNavigateToVideo, onNavigateHome }: TransformPageProps) {
  // Session state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Upload state
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  
  // Presets state
  const [presets, setPresets] = useState<TransformPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>('');
  const [customPrompt, setCustomPrompt] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  
  // Transform state
  const [isTransforming, setIsTransforming] = useState(false);
  const [transformedImageUrl, setTransformedImageUrl] = useState<string | null>(null);
  const [transformComplete, setTransformComplete] = useState(false);
  
  // Initialize session and load presets
  useEffect(() => {
    const init = async () => {
      try {
        const [sessionResult, presetsResult] = await Promise.all([
          createSession(),
          getTransformPresets()
        ]);
        setSessionId(sessionResult.session_id);
        setPresets(presetsResult.presets);
        if (presetsResult.presets.length > 0) {
          setSelectedPreset(presetsResult.presets[0].key);
        }
      } catch (err) {
        setError('Failed to connect to server. Make sure the backend is running.');
        console.error(err);
      }
    };
    init();
  }, []);
  
  // Handle image upload
  const handleImageUpload = useCallback(async (file: File) => {
    if (!sessionId) return;
    
    try {
      setError(null);
      setIsUploading(true);
      setTransformComplete(false);
      setTransformedImageUrl(null);
      
      // Show preview immediately
      setImagePreview(URL.createObjectURL(file));
      setImageFile(file);
      
      await uploadImage(sessionId, file);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload image');
      setImageFile(null);
      setImagePreview(null);
    } finally {
      setIsUploading(false);
    }
  }, [sessionId]);
  
  // Handle file drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      handleImageUpload(file);
    }
  }, [handleImageUpload]);
  
  // Handle file input change
  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleImageUpload(file);
    }
  }, [handleImageUpload]);
  
  // Handle transform
  const handleTransform = useCallback(async () => {
    if (!sessionId || !imageFile || !selectedPreset) return;
    
    try {
      setError(null);
      setIsTransforming(true);
      setTransformComplete(false);
      
      await transformImage(
        sessionId, 
        selectedPreset,
        selectedPreset === 'custom' ? customPrompt : undefined
      );
      
      // Poll for completion
      const pollStatus = async () => {
        const status = await getTransformStatus(sessionId);
        
        if (status.status === 'complete') {
          setIsTransforming(false);
          setTransformComplete(true);
          // Add timestamp to bust cache
          setTransformedImageUrl(`${getSessionImageUrl(sessionId, 'transformed')}?t=${Date.now()}`);
        } else if (status.status === 'error') {
          setIsTransforming(false);
          setError('Transformation failed. Please try again.');
        } else {
          setTimeout(pollStatus, 1000);
        }
      };
      
      pollStatus();
    } catch (err) {
      setIsTransforming(false);
      setError(err instanceof Error ? err.message : 'Failed to transform image');
    }
  }, [sessionId, imageFile, selectedPreset, customPrompt]);
  
  // Handle use in video
  const handleUseInVideo = useCallback(() => {
    if (sessionId && transformComplete) {
      onNavigateToVideo(sessionId);
    }
  }, [sessionId, transformComplete, onNavigateToVideo]);
  
  const selectedPresetData = presets.find(p => p.key === selectedPreset);
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <button 
            onClick={onNavigateHome}
            className="flex items-center gap-3 hover:opacity-80 transition-opacity"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 to-teal-500 flex items-center justify-center shadow-lg shadow-cyan-500/30">
              <Wand2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-display text-xl font-bold text-white">Image Transform</h1>
              <p className="text-sm text-white/50">AI-powered style transfer</p>
            </div>
          </button>
          
          <a
            href="#/"
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
          >
            <Sparkles className="w-4 h-4" />
            Video Creator
          </a>
        </div>
      </header>
      
      {/* Error Banner */}
      {error && (
        <div className="max-w-6xl mx-auto px-6 pt-4">
          <div className="bg-red-500/20 border border-red-500/30 text-red-200 px-4 py-3 rounded-lg">
            {error}
          </div>
        </div>
      )}
      
      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-12">
        <div className="text-center mb-10">
          <h2 className="font-display text-3xl font-bold text-white mb-3">
            Transform Your Cover Art
          </h2>
          <p className="text-white/60 max-w-xl mx-auto">
            Apply AI-powered style presets to create stunning variations of your artwork, 
            then use the result in the video creator.
          </p>
        </div>
        
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left: Upload & Controls */}
          <div className="space-y-6">
            {/* Upload Zone */}
            <div 
              className={`relative border-2 border-dashed rounded-2xl transition-all ${
                imageFile 
                  ? 'border-cyan-500/50 bg-cyan-500/5' 
                  : 'border-white/20 hover:border-white/40 bg-white/5'
              }`}
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
            >
              {imagePreview ? (
                <div className="p-4">
                  <div className="relative aspect-square rounded-xl overflow-hidden bg-black/50">
                    <img 
                      src={imagePreview} 
                      alt="Original" 
                      className="w-full h-full object-contain"
                    />
                    <div className="absolute top-3 left-3 px-2 py-1 bg-black/60 rounded text-xs text-white/80">
                      Original
                    </div>
                  </div>
                  <label className="mt-4 flex items-center justify-center gap-2 py-2 text-sm text-white/60 hover:text-white cursor-pointer transition-colors">
                    <RefreshCw className="w-4 h-4" />
                    Change Image
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleFileChange}
                      className="hidden"
                    />
                  </label>
                </div>
              ) : (
                <label className="flex flex-col items-center justify-center p-12 cursor-pointer">
                  <div className="w-16 h-16 rounded-2xl bg-white/10 flex items-center justify-center mb-4">
                    {isUploading ? (
                      <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
                    ) : (
                      <Upload className="w-8 h-8 text-white/60" />
                    )}
                  </div>
                  <span className="text-lg font-medium text-white mb-2">
                    {isUploading ? 'Uploading...' : 'Drop your image here'}
                  </span>
                  <span className="text-sm text-white/50">
                    or click to browse
                  </span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileChange}
                    className="hidden"
                    disabled={isUploading}
                  />
                </label>
              )}
            </div>
            
            {/* Preset Selector */}
            <div className="bg-white/5 rounded-2xl border border-white/10 p-5">
              <label className="text-sm font-medium text-white/80 block mb-3">
                Style Preset
              </label>
              
              <div className="relative">
                <button
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="w-full flex items-center justify-between px-4 py-3 bg-white/10 rounded-xl text-left hover:bg-white/15 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {selectedPresetData && (
                      <div 
                        className="w-4 h-4 rounded-full"
                        style={{ backgroundColor: selectedPresetData.thumbnail_color }}
                      />
                    )}
                    <span className="text-white font-medium">
                      {selectedPresetData?.name || 'Select a preset'}
                    </span>
                  </div>
                  <ChevronDown className={`w-5 h-5 text-white/50 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
                </button>
                
                {isDropdownOpen && (
                  <div className="absolute top-full left-0 right-0 mt-2 bg-slate-800 border border-white/10 rounded-xl overflow-hidden shadow-xl z-10">
                    {presets.map((preset) => (
                      <button
                        key={preset.key}
                        onClick={() => {
                          setSelectedPreset(preset.key);
                          setIsDropdownOpen(false);
                        }}
                        className={`w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-white/10 transition-colors ${
                          selectedPreset === preset.key ? 'bg-white/10' : ''
                        }`}
                      >
                        <div 
                          className="w-4 h-4 rounded-full mt-0.5 flex-shrink-0"
                          style={{ backgroundColor: preset.thumbnail_color }}
                        />
                        <div>
                          <div className="text-white font-medium">{preset.name}</div>
                          <div className="text-sm text-white/50">{preset.description}</div>
                        </div>
                      </button>
                    ))}
                    
                    {/* Custom option */}
                    <button
                      onClick={() => {
                        setSelectedPreset('custom');
                        setIsDropdownOpen(false);
                      }}
                      className={`w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-white/10 transition-colors border-t border-white/10 ${
                        selectedPreset === 'custom' ? 'bg-white/10' : ''
                      }`}
                    >
                      <div className="w-4 h-4 rounded-full mt-0.5 flex-shrink-0 bg-gradient-to-br from-pink-500 to-orange-500" />
                      <div>
                        <div className="text-white font-medium">Custom Prompt</div>
                        <div className="text-sm text-white/50">Write your own transformation prompt</div>
                      </div>
                    </button>
                  </div>
                )}
              </div>
              
              {/* Custom prompt textarea */}
              {selectedPreset === 'custom' && (
                <div className="mt-4">
                  <textarea
                    value={customPrompt}
                    onChange={(e) => setCustomPrompt(e.target.value)}
                    placeholder="Describe how you want to transform the image..."
                    className="w-full h-32 px-4 py-3 bg-white/10 border border-white/10 rounded-xl text-white placeholder-white/30 resize-none focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                  />
                </div>
              )}
              
              {/* Preset description */}
              {selectedPresetData && selectedPreset !== 'custom' && (
                <p className="mt-3 text-sm text-white/50">
                  {selectedPresetData.description}
                </p>
              )}
            </div>
            
            {/* Transform Button */}
            <button
              onClick={handleTransform}
              disabled={!imageFile || !selectedPreset || isTransforming || (selectedPreset === 'custom' && !customPrompt)}
              className="w-full py-4 bg-gradient-to-r from-cyan-500 to-teal-500 text-white font-semibold rounded-xl hover:from-cyan-400 hover:to-teal-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/30 flex items-center justify-center gap-2"
            >
              {isTransforming ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Transforming...
                </>
              ) : (
                <>
                  <Wand2 className="w-5 h-5" />
                  Transform Image
                </>
              )}
            </button>
          </div>
          
          {/* Right: Result Preview */}
          <div className="space-y-6">
            <div className="bg-white/5 rounded-2xl border border-white/10 p-5 min-h-[400px] flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-medium text-white/80">Transformed Result</span>
                {transformComplete && (
                  <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">
                    Complete
                  </span>
                )}
              </div>
              
              {isTransforming ? (
                <div className="flex-1 flex flex-col items-center justify-center">
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-teal-500/20 flex items-center justify-center mb-4">
                    <Loader2 className="w-10 h-10 text-cyan-400 animate-spin" />
                  </div>
                  <p className="text-white/60 text-center">
                    AI is transforming your image...<br />
                    <span className="text-sm text-white/40">This may take 30-60 seconds</span>
                  </p>
                </div>
              ) : transformedImageUrl ? (
                <div className="flex-1">
                  <div className="relative aspect-square rounded-xl overflow-hidden bg-black/50">
                    <img 
                      src={transformedImageUrl} 
                      alt="Transformed" 
                      className="w-full h-full object-contain"
                    />
                    <div className="absolute top-3 left-3 px-2 py-1 bg-black/60 rounded text-xs text-white/80">
                      Transformed
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center">
                  <div className="w-20 h-20 rounded-2xl bg-white/5 flex items-center justify-center mb-4">
                    <ImageIcon className="w-10 h-10 text-white/20" />
                  </div>
                  <p className="text-white/40 text-center">
                    Upload an image and select a preset<br />
                    to see the transformation
                  </p>
                </div>
              )}
            </div>
            
            {/* Use in Video Button */}
            {transformComplete && (
              <button
                onClick={handleUseInVideo}
                className="w-full py-4 bg-gradient-to-r from-violet-500 to-purple-600 text-white font-semibold rounded-xl hover:from-violet-400 hover:to-purple-500 transition-all shadow-lg shadow-purple-500/30 flex items-center justify-center gap-2"
              >
                Use in Video Creator
                <ArrowRight className="w-5 h-5" />
              </button>
            )}
            
            {/* Side by side comparison when both available */}
            {imagePreview && transformedImageUrl && (
              <div className="bg-white/5 rounded-2xl border border-white/10 p-5">
                <span className="text-sm font-medium text-white/80 block mb-4">Before & After</span>
                <div className="grid grid-cols-2 gap-4">
                  <div className="relative aspect-square rounded-lg overflow-hidden bg-black/50">
                    <img src={imagePreview} alt="Before" className="w-full h-full object-cover" />
                    <div className="absolute bottom-2 left-2 px-2 py-0.5 bg-black/60 rounded text-xs text-white/80">
                      Before
                    </div>
                  </div>
                  <div className="relative aspect-square rounded-lg overflow-hidden bg-black/50">
                    <img src={transformedImageUrl} alt="After" className="w-full h-full object-cover" />
                    <div className="absolute bottom-2 left-2 px-2 py-0.5 bg-black/60 rounded text-xs text-white/80">
                      After
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

