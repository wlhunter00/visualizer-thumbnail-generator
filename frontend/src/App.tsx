import { useState, useEffect, useCallback } from 'react';
import { 
  Step, 
  GenerateSettings, 
  Playbook, 
  ASPECT_RATIOS, 
  EffectToggles, 
  DEFAULT_EFFECT_TOGGLES,
  ImageAnalysis 
} from './types';
import { 
  createSession, 
  uploadImage, 
  uploadAudio, 
  getWaveform, 
  generateVideo, 
  getGenerationStatus, 
  exportVideo, 
  getPreviewUrl, 
  getDownloadUrl,
  analyzeImage,
  autoSuggest
} from './api';
import StepIndicator from './components/StepIndicator';
import UploadStep from './components/UploadStep';
import WaveformSelector from './components/WaveformSelector';
import EffectControls from './components/EffectControls';
import VideoPreview from './components/VideoPreview';
import { Music, Image as ImageIcon, Sparkles, Download, Loader2 } from 'lucide-react';

export default function App() {
  // Session state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<Step>(1);
  
  // Upload state
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null);
  const [audioDuration, setAudioDuration] = useState<number>(0);
  const [waveformData, setWaveformData] = useState<[number, number][]>([]);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [isUploadingAudio, setIsUploadingAudio] = useState(false);
  
  // NEW: Image analysis state
  const [imageAnalysis, setImageAnalysis] = useState<ImageAnalysis | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isAutoSuggesting, setIsAutoSuggesting] = useState(false);
  
  // Settings state - now using effect toggles
  const [effectToggles, setEffectToggles] = useState<EffectToggles>(DEFAULT_EFFECT_TOGGLES);
  const [settings, setSettings] = useState<GenerateSettings>({
    start_time: 0,
    end_time: 30,
    aspect_ratio: '9:16',
    effect_toggles: DEFAULT_EFFECT_TOGGLES,
  });
  
  // Generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [videoReady, setVideoReady] = useState(false);
  const [playbook, setPlaybook] = useState<Playbook | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Export state
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  
  // Initialize session
  useEffect(() => {
    createSession().then(({ session_id }) => {
      setSessionId(session_id);
    }).catch(err => {
      setError('Failed to connect to server. Make sure the backend is running.');
      console.error(err);
    });
  }, []);
  
  // Handle image upload
  const handleImageUpload = useCallback(async (file: File) => {
    if (!sessionId) return;
    
    try {
      setError(null);
      setIsUploadingImage(true);
      
      // Show preview immediately
      setImagePreview(URL.createObjectURL(file));
      setImageFile(file);
      
      await uploadImage(sessionId, file);
      
      // Reset analysis when new image uploaded
      setImageAnalysis(null);
      
      // Auto-advance if audio is already uploaded
      if (audioFile) {
        setCurrentStep(3);
      } else {
        setCurrentStep(2);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload image');
      setImageFile(null);
      setImagePreview(null);
    } finally {
      setIsUploadingImage(false);
    }
  }, [sessionId, audioFile]);
  
  // Handle audio upload
  const handleAudioUpload = useCallback(async (file: File) => {
    if (!sessionId) return;
    
    try {
      setError(null);
      setIsUploadingAudio(true);
      setAudioFile(file);
      
      // Create local blob URL for instant playback preview
      const localAudioUrl = URL.createObjectURL(file);
      setAudioPreviewUrl(localAudioUrl);
      
      const { duration } = await uploadAudio(sessionId, file);
      setAudioDuration(duration);
      setSettings(s => ({
        ...s,
        end_time: Math.min(30, duration),
      }));
      
      // Get waveform
      const { waveform } = await getWaveform(sessionId);
      setWaveformData(waveform);
      
      // Auto-advance if image is already uploaded
      if (imageFile) {
        setCurrentStep(3);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload audio');
      setAudioFile(null);
      setAudioPreviewUrl(null);
    } finally {
      setIsUploadingAudio(false);
    }
  }, [sessionId, imageFile]);
  
  // Handle region selection
  const handleRegionChange = useCallback((start: number, end: number) => {
    setSettings(s => ({ ...s, start_time: start, end_time: end }));
  }, []);
  
  // Handle aspect ratio change
  const handleAspectRatioChange = useCallback((value: string) => {
    setSettings(s => ({ ...s, aspect_ratio: value }));
    setVideoReady(false);
  }, []);
  
  // Handle effect toggles change
  const handleEffectTogglesChange = useCallback((toggles: EffectToggles) => {
    setEffectToggles(toggles);
    setSettings(s => ({ ...s, effect_toggles: toggles }));
    setVideoReady(false);
  }, []);
  
  // NEW: Handle auto-suggest
  const handleAutoSuggest = useCallback(async () => {
    if (!sessionId) return;
    
    try {
      setError(null);
      setIsAutoSuggesting(true);
      
      const result = await autoSuggest(sessionId);
      
      // Update effect toggles with suggestions
      setEffectToggles(result.effect_toggles);
      setSettings(s => ({ ...s, effect_toggles: result.effect_toggles }));
      
      // Also update image analysis if we got it
      // (auto-suggest runs image analysis if not already done)
      if (!imageAnalysis) {
        try {
          const analysisResult = await analyzeImage(sessionId);
          setImageAnalysis(analysisResult.analysis);
        } catch {
          // Ignore - analysis might have already been done
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get auto-suggestions');
    } finally {
      setIsAutoSuggesting(false);
    }
  }, [sessionId, imageAnalysis]);
  
  // NEW: Analyze image when entering step 3
  useEffect(() => {
    if (currentStep === 3 && sessionId && imageFile && !imageAnalysis && !isAnalyzing) {
      setIsAnalyzing(true);
      analyzeImage(sessionId)
        .then(result => {
          setImageAnalysis(result.analysis);
        })
        .catch(err => {
          // Non-fatal - continue without analysis
          console.warn('Image analysis failed:', err);
        })
        .finally(() => {
          setIsAnalyzing(false);
        });
    }
  }, [currentStep, sessionId, imageFile, imageAnalysis, isAnalyzing]);
  
  // Generate video
  const handleGenerate = useCallback(async () => {
    if (!sessionId) return;
    
    try {
      setError(null);
      setIsGenerating(true);
      setProgress(0);
      setVideoReady(false);
      
      await generateVideo(sessionId, {
        ...settings,
        effect_toggles: effectToggles,
      });
      
      // Poll for completion
      const pollStatus = async () => {
        const status = await getGenerationStatus(sessionId);
        setProgress(status.progress * 100);
        
        if (status.status === 'complete') {
          setIsGenerating(false);
          setVideoReady(true);
          setPlaybook(status.playbook);
          setCurrentStep(4);
        } else if (status.status === 'error') {
          setIsGenerating(false);
          setError('Generation failed. Please try again.');
        } else {
          setTimeout(pollStatus, 500);
        }
      };
      
      pollStatus();
    } catch (err) {
      setIsGenerating(false);
      setError(err instanceof Error ? err.message : 'Failed to generate video');
    }
  }, [sessionId, settings, effectToggles]);
  
  // Export video
  const handleExport = useCallback(async () => {
    if (!sessionId) return;
    
    try {
      setError(null);
      setIsExporting(true);
      setExportProgress(0);
      
      await exportVideo(sessionId);
      
      // Poll for export completion
      const pollExportStatus = async () => {
        const status = await getGenerationStatus(sessionId);
        setExportProgress(status.progress * 100);
        
        if (status.status === 'export_complete') {
          setIsExporting(false);
          // Trigger download
          const link = document.createElement('a');
          link.href = getDownloadUrl(sessionId);
          link.download = 'beat-reactive-video.mp4';
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        } else if (status.status === 'error') {
          setIsExporting(false);
          setError('Export failed. Please try again.');
        } else {
          setTimeout(pollExportStatus, 500);
        }
      };
      
      pollExportStatus();
    } catch (err) {
      setIsExporting(false);
      setError(err instanceof Error ? err.message : 'Failed to export video');
    }
  }, [sessionId]);
  
  const canGenerate = imageFile && audioFile && settings.end_time > settings.start_time;
  const selectedDuration = settings.end_time - settings.start_time;
  
  return (
    <div className="min-h-screen bg-surface-50">
      {/* Header */}
      <header className="border-b border-surface-200 bg-white">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg shadow-purple-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-display text-xl font-bold text-surface-900">Beat Visualizer</h1>
              <p className="text-sm text-surface-500">AI-powered music videos</p>
            </div>
          </div>
        </div>
      </header>
      
      {/* Step Indicator */}
      <div className="border-b border-surface-200 bg-white">
        <div className="max-w-5xl mx-auto px-6 py-4">
          <StepIndicator currentStep={currentStep} />
        </div>
      </div>
      
      {/* Error Banner */}
      {error && (
        <div className="max-w-5xl mx-auto px-6 pt-4">
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        </div>
      )}
      
      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Step 1 & 2: Upload */}
        {(currentStep === 1 || currentStep === 2) && (
          <div className="animate-fade-in">
            <div className="text-center mb-8">
              <h2 className="font-display text-2xl font-bold text-surface-900 mb-2">
                {currentStep === 1 ? 'Upload Your Cover Art' : 'Upload Your Track'}
              </h2>
              <p className="text-surface-500">
                {currentStep === 1 
                  ? 'Start with the image that will be animated'
                  : 'Add the music that will drive the visuals'}
              </p>
            </div>
            
            <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
              <UploadStep
                type="image"
                file={imageFile}
                preview={imagePreview}
                onUpload={handleImageUpload}
                active={currentStep === 1}
                loading={isUploadingImage}
                icon={<ImageIcon className="w-8 h-8" />}
              />
              <UploadStep
                type="audio"
                file={audioFile}
                duration={audioDuration}
                onUpload={handleAudioUpload}
                active={currentStep === 2}
                loading={isUploadingAudio}
                icon={<Music className="w-8 h-8" />}
              />
            </div>
          </div>
        )}
        
        {/* Step 3: Adjust */}
        {currentStep === 3 && (
          <div className="animate-fade-in">
            <div className="text-center mb-8">
              <h2 className="font-display text-2xl font-bold text-surface-900 mb-2">
                Customize Your Effects
              </h2>
              <p className="text-surface-500">
                Select effects and adjust intensities, or let AI suggest settings
              </p>
            </div>
            
            <div className="grid lg:grid-cols-3 gap-8">
              {/* Left: Preview & Waveform */}
              <div className="lg:col-span-2 space-y-6">
                {/* Image Preview with Analysis Indicator */}
                {imagePreview && (
                  <div className="bg-white rounded-2xl border border-surface-200 p-4">
                    <div className="relative aspect-video bg-surface-100 rounded-xl overflow-hidden flex items-center justify-center">
                      <img 
                        src={imagePreview} 
                        alt="Cover art preview" 
                        className="max-w-full max-h-full object-contain"
                      />
                      {isAnalyzing && (
                        <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                          <div className="bg-white rounded-lg px-4 py-2 flex items-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin text-accent" />
                            <span className="text-sm text-surface-700">Analyzing image...</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Waveform */}
                <div className="bg-white rounded-2xl border border-surface-200 p-4">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-medium text-surface-700">Audio Region</span>
                    <span className="text-sm text-surface-500">
                      {selectedDuration.toFixed(1)}s selected
                    </span>
                  </div>
                  <WaveformSelector
                    waveformData={waveformData}
                    duration={audioDuration}
                    startTime={settings.start_time}
                    endTime={settings.end_time}
                    onRegionChange={handleRegionChange}
                    audioUrl={audioPreviewUrl || undefined}
                  />
                </div>
              </div>
              
              {/* Right: Controls */}
              <div className="space-y-6">
                {/* Aspect Ratio */}
                <div className="bg-white rounded-2xl border border-surface-200 p-4">
                  <span className="text-sm font-medium text-surface-700 block mb-3">Aspect Ratio</span>
                  <div className="grid grid-cols-2 gap-2">
                    {ASPECT_RATIOS.map((ratio) => (
                      <button
                        key={ratio.value}
                        onClick={() => handleAspectRatioChange(ratio.value)}
                        className={`p-3 rounded-xl text-left transition-all ${
                          settings.aspect_ratio === ratio.value
                            ? 'bg-accent text-white'
                            : 'bg-surface-100 hover:bg-surface-200 text-surface-700'
                        }`}
                      >
                        <div className="text-sm font-medium">{ratio.label}</div>
                        <div className={`text-xs ${
                          settings.aspect_ratio === ratio.value ? 'text-white/70' : 'text-surface-500'
                        }`}>
                          {ratio.description}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
                
                {/* Effect Controls */}
                <EffectControls
                  effectToggles={effectToggles}
                  onChange={handleEffectTogglesChange}
                  onAutoSuggest={handleAutoSuggest}
                  isAutoSuggesting={isAutoSuggesting}
                  imageAnalysis={imageAnalysis}
                />
                
                {/* Generate Button */}
                <button
                  onClick={handleGenerate}
                  disabled={!canGenerate || isGenerating}
                  className="w-full py-4 bg-accent text-white font-medium rounded-xl hover:bg-accent-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isGenerating ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Generating... {Math.round(progress)}%
                    </span>
                  ) : (
                    'Generate Video'
                  )}
                </button>
                
                {isGenerating && (
                  <div className="h-2 bg-surface-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full progress-bar rounded-full"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
        
        {/* Step 4: Preview & Export */}
        {currentStep === 4 && sessionId && (
          <div className="animate-fade-in">
            <div className="text-center mb-8">
              <h2 className="font-display text-2xl font-bold text-surface-900 mb-2">
                Preview & Export
              </h2>
              <p className="text-surface-500">
                Review your video and make any final adjustments
              </p>
            </div>
            
            <div className="grid lg:grid-cols-3 gap-8">
              {/* Video Preview */}
              <div className="lg:col-span-2">
                <VideoPreview
                  videoUrl={getPreviewUrl(sessionId)}
                  aspectRatio={settings.aspect_ratio}
                />
                
                {/* Playbook Summary */}
                {playbook && (
                  <div className="mt-4 bg-white rounded-2xl border border-surface-200 p-4">
                    <h3 className="text-sm font-medium text-surface-700 mb-2">Generation Summary</h3>
                    <p className="text-sm text-surface-600 mb-3">{playbook.summary}</p>
                    
                    {playbook.active_effects && playbook.active_effects.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {playbook.active_effects.map((effect, i) => (
                          <span 
                            key={i}
                            className="text-xs px-2 py-1 bg-accent/10 text-accent rounded-full"
                          >
                            {effect}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              {/* Controls & Actions */}
              <div className="space-y-6">
                <EffectControls
                  effectToggles={effectToggles}
                  onChange={handleEffectTogglesChange}
                  onAutoSuggest={handleAutoSuggest}
                  isAutoSuggesting={isAutoSuggesting}
                  imageAnalysis={imageAnalysis}
                />
                
                <div className="space-y-3">
                  <button
                    onClick={handleExport}
                    disabled={isExporting}
                    className="w-full py-4 bg-gradient-to-r from-violet-500 to-purple-600 text-white font-medium rounded-xl hover:from-violet-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-purple-500/20"
                  >
                    {isExporting ? 'Exporting...' : 'Export High Quality'}
                  </button>
                  
                  <button
                    onClick={handleGenerate}
                    disabled={isGenerating}
                    className="w-full py-3 bg-white border border-surface-200 text-surface-700 font-medium rounded-xl hover:bg-surface-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isGenerating ? `Re-rendering... ${Math.round(progress)}%` : 'Re-render Video'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
      
      {/* Export Modal */}
      {isExporting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl animate-fade-in">
            <div className="flex flex-col items-center text-center">
              {/* Animated icon */}
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-violet-100 to-purple-100 flex items-center justify-center mb-6">
                <Download className="w-8 h-8 text-violet-600 animate-pulse" />
              </div>
              
              <h3 className="font-display text-xl font-bold text-surface-900 mb-2">
                Exporting Your Video
              </h3>
              <p className="text-surface-500 mb-6">
                Rendering at full quality. This may take a moment.
              </p>
              
              {/* Progress bar */}
              <div className="w-full mb-4">
                <div className="h-3 bg-surface-200 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-violet-500 to-purple-600 rounded-full transition-all duration-300"
                    style={{ width: `${exportProgress}%` }}
                  />
                </div>
              </div>
              
              <span className="text-2xl font-display font-bold bg-gradient-to-r from-violet-600 to-purple-600 bg-clip-text text-transparent">
                {Math.round(exportProgress)}%
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
