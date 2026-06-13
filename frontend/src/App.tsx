import { useState, useEffect, useCallback, useRef } from 'react';
import { 
  Step, 
  GenerateSettings, 
  ASPECT_RATIOS, 
  EffectToggles, 
  DEFAULT_EFFECT_TOGGLES,
  ImageAnalysis,
  AudioFeatures,
  RENDER_RESOLUTIONS
} from './types';
import { 
  createSession, 
  uploadImage, 
  uploadAudio, 
  getWaveform, 
  getGenerationStatus, 
  exportVideo, 
  getDownloadUrl,
  analyzeImage,
  autoSuggest,
  getAudioAnalysis,
  syncSessionSettings,
  generateParticles,
} from './api';
import StepIndicator from './components/StepIndicator';
import UploadStep from './components/UploadStep';
import WaveformSelector from './components/WaveformSelector';
import EffectControls from './components/EffectControls';
import LivePreviewCanvas from './components/LivePreviewCanvas';
import RenderSettings from './components/RenderSettings';
import DemoPage from './DemoPage';
import TransformPage from './TransformPage';
import { AudioPreviewProvider } from './context/AudioPreviewContext';
import { Music, Image as ImageIcon, Sparkles, Download, Loader2, PlayCircle, Wand2 } from 'lucide-react';

// Parse hash route
function parseHash(): { page: 'main' | 'demo' | 'transform'; effectKey?: string; sessionId?: string } {
  const hash = window.location.hash;
  if (hash.startsWith('#/demo')) {
    const parts = hash.split('/');
    const effectKey = parts[2] || undefined;
    return { page: 'demo', effectKey };
  }
  if (hash.startsWith('#/transform')) {
    return { page: 'transform' };
  }
  // Check for session ID from transform flow: #/video/{sessionId}
  if (hash.startsWith('#/video/')) {
    const sessionId = hash.split('/')[2];
    return { page: 'main', sessionId };
  }
  return { page: 'main' };
}

interface MainAppProps {
  initialSessionId?: string;
}

function MainApp({ initialSessionId }: MainAppProps) {
  // Session state
  const [sessionId, setSessionId] = useState<string | null>(initialSessionId || null);
  const [currentStep, setCurrentStep] = useState<Step>(initialSessionId ? 2 : 1);
  
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
  const [hasAttemptedAnalysis, setHasAttemptedAnalysis] = useState(false);
  const [isAutoSuggesting, setIsAutoSuggesting] = useState(false);
  
  // Settings state - now using effect toggles
  const [effectToggles, setEffectToggles] = useState<EffectToggles>(DEFAULT_EFFECT_TOGGLES);
  const [resolution, setResolution] = useState<string>('1080p');
  const [settings, setSettings] = useState<GenerateSettings>({
    start_time: 0,
    end_time: 30,
    aspect_ratio: '9:16',
    effect_toggles: DEFAULT_EFFECT_TOGGLES,
  });
  
  // Live preview state
  const [audioAnalysis, setAudioAnalysis] = useState<AudioFeatures | null>(null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);
  const syncDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastRegionRef = useRef<string>('');
  
  // Export state
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [exportStatusLabel, setExportStatusLabel] = useState<string | null>(null);
  const [exportAspectRatios, setExportAspectRatios] = useState<string[]>(['9:16']);
  const [error, setError] = useState<string | null>(null);
  
  // Initialize session (skip if we have one from transform flow)
  useEffect(() => {
    if (initialSessionId) {
      // Session already set from transform flow, mark image as ready
      setSessionId(initialSessionId);
      // Fetch the transformed image to show preview
      fetch(`/api/image/${initialSessionId}/current`)
        .then(res => {
          if (res.ok) {
            setImagePreview(`/api/image/${initialSessionId}/current?t=${Date.now()}`);
            setImageFile(new File([], 'transformed.png')); // Placeholder to enable flow
          }
        })
        .catch(() => {});
      return;
    }
    
    createSession().then(({ session_id }) => {
      setSessionId(session_id);
    }).catch(err => {
      setError('Failed to connect to server. Make sure the backend is running.');
      console.error(err);
    });
  }, [initialSessionId]);
  
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
      setHasAttemptedAnalysis(false);
      
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
  
  // Handle aspect ratio change (preview only; export selection is separate)
  const handleAspectRatioChange = useCallback((value: string) => {
    const oldRatio = settings.aspect_ratio;
    setSettings(s => ({ ...s, aspect_ratio: value }));
    setExportAspectRatios(prev =>
      prev.length === 1 && prev[0] === oldRatio ? [value] : prev
    );
  }, [settings.aspect_ratio]);

  const handleExportAspectRatioToggle = useCallback((value: string) => {
    setExportAspectRatios(prev => {
      if (prev.includes(value)) {
        if (prev.length === 1) return prev;
        return prev.filter(r => r !== value);
      }
      return [...prev, value];
    });
  }, []);

  // Handle resolution change
  const handleResolutionChange = useCallback((value: string) => {
    setResolution(value);
  }, []);
  
  // Handle effect toggles change
  const handleEffectTogglesChange = useCallback((toggles: EffectToggles) => {
    setEffectToggles(toggles);
    setSettings(s => ({ ...s, effect_toggles: toggles }));
  }, []);

  const handleLoadPreset = useCallback((toggles: EffectToggles) => {
    handleEffectTogglesChange(toggles);
  }, [handleEffectTogglesChange]);
  
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
  
  // Analyze image once when entering step 3 (skip retry if it already failed)
  useEffect(() => {
    if (currentStep === 3 && sessionId && imageFile && !imageAnalysis && !isAnalyzing && !hasAttemptedAnalysis) {
      setHasAttemptedAnalysis(true);
      setIsAnalyzing(true);
      analyzeImage(sessionId)
        .then(result => {
          setImageAnalysis(result.analysis);
          generateParticles(sessionId).catch(() => {});
        })
        .catch(err => {
          // Non-fatal - continue without analysis
          console.warn('Image analysis failed:', err);
        })
        .finally(() => {
          setIsAnalyzing(false);
        });
    }
  }, [currentStep, sessionId, imageFile, imageAnalysis, isAnalyzing, hasAttemptedAnalysis]);
  
  // Reset session state when files are missing on backend
  const handleSessionReset = useCallback(async () => {
    // Create a new session and reset all state
    try {
      const { session_id } = await createSession();
      setSessionId(session_id);
      setImageFile(null);
      setImagePreview(null);
      setAudioFile(null);
      setAudioPreviewUrl(null);
      setAudioDuration(0);
      setWaveformData([]);
      setImageAnalysis(null);
      setHasAttemptedAnalysis(false);
      setEffectToggles(DEFAULT_EFFECT_TOGGLES);
      setSettings({
        start_time: 0,
        end_time: 30,
        aspect_ratio: '9:16',
        effect_toggles: DEFAULT_EFFECT_TOGGLES,
      });
      setExportAspectRatios(['9:16']);
      setAudioAnalysis(null);
      setCurrentStep(1);
      setError('Your session expired. Please re-upload your files.');
    } catch (e) {
      setError('Failed to create new session. Please refresh the page.');
    }
  }, []);

  const fetchAudioAnalysis = useCallback(async (sid: string) => {
    setIsLoadingAnalysis(true);
    try {
      const analysis = await getAudioAnalysis(sid);
      setAudioAnalysis(analysis);
    } catch (err) {
      console.warn('Audio analysis failed:', err);
    } finally {
      setIsLoadingAnalysis(false);
    }
  }, []);

  const syncAndMaybeAnalyze = useCallback((
    sid: string,
    currentSettings: GenerateSettings,
    toggles: EffectToggles,
    regionChanged: boolean
  ) => {
    syncSessionSettings(sid, {
      start_time: currentSettings.start_time,
      end_time: currentSettings.end_time,
      aspect_ratio: currentSettings.aspect_ratio,
      effect_toggles: toggles,
    }).then(() => {
      if (regionChanged) fetchAudioAnalysis(sid);
    }).catch(err => console.warn('Session sync failed:', err));
  }, [fetchAudioAnalysis]);

  // Sync settings and fetch audio analysis when entering step 3
  useEffect(() => {
    if (currentStep !== 3 || !sessionId || !audioFile) return;

    const regionKey = `${settings.start_time}:${settings.end_time}`;
    lastRegionRef.current = regionKey;

    syncSessionSettings(sessionId, {
      start_time: settings.start_time,
      end_time: settings.end_time,
      aspect_ratio: settings.aspect_ratio,
      effect_toggles: effectToggles,
    }).then(() => fetchAudioAnalysis(sessionId)).catch(err => {
      console.warn('Initial sync failed:', err);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep, sessionId, audioFile]);

  // Debounced sync on settings changes while on step 3
  useEffect(() => {
    if (currentStep !== 3 || !sessionId) return;

    if (syncDebounceRef.current) clearTimeout(syncDebounceRef.current);
    syncDebounceRef.current = setTimeout(() => {
      const regionKey = `${settings.start_time}:${settings.end_time}`;
      const regionChanged = lastRegionRef.current !== regionKey;
      if (regionChanged) lastRegionRef.current = regionKey;
      syncAndMaybeAnalyze(sessionId, settings, effectToggles, regionChanged);
    }, 300);

    return () => {
      if (syncDebounceRef.current) clearTimeout(syncDebounceRef.current);
    };
  }, [settings.start_time, settings.end_time, settings.aspect_ratio, effectToggles, currentStep, sessionId, syncAndMaybeAnalyze, settings]);
  
  // Export video
  const handleExport = useCallback(async () => {
    if (!sessionId || exportAspectRatios.length === 0) return;
    
    try {
      setError(null);
      setIsExporting(true);
      setExportProgress(0);
      setExportStatusLabel(null);
      
      // Get resolution scale from selected resolution
      const selectedRes = RENDER_RESOLUTIONS.find(r => r.value === resolution);
      const resolutionScale = selectedRes?.scale || 1.0;

      await syncSessionSettings(sessionId, {
        start_time: settings.start_time,
        end_time: settings.end_time,
        aspect_ratio: settings.aspect_ratio,
        effect_toggles: effectToggles,
      });

      await exportVideo(sessionId, resolutionScale, {
        start_time: settings.start_time,
        end_time: settings.end_time,
        aspect_ratio: settings.aspect_ratio,
        aspect_ratios: exportAspectRatios,
        effect_toggles: effectToggles,
      });
      
      // Poll for export completion
      const pollExportStatus = async () => {
        const status = await getGenerationStatus(sessionId);
        setExportProgress(status.progress * 100);

        if (status.export_total && status.export_total > 1) {
          const completed = status.export_completed ?? 0;
          const current = status.export_current_ratio ?? '';
          setExportStatusLabel(
            status.status === 'export_complete'
              ? null
              : `Exporting ${Math.min(completed + 1, status.export_total)}/${status.export_total} — ${current}`
          );
        } else if (status.export_current_ratio && status.status === 'exporting') {
          setExportStatusLabel(`Exporting ${status.export_current_ratio}`);
        }
        
        if (status.status === 'export_complete') {
          setIsExporting(false);
          setExportStatusLabel(null);

          const files = status.export_files ?? [];
          if (files.length > 0) {
            for (const file of files) {
              await new Promise(resolve => setTimeout(resolve, 300));
              const link = document.createElement('a');
              link.href = getDownloadUrl(sessionId, file.aspect_ratio);
              link.download = file.filename;
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
            }
          } else {
            const link = document.createElement('a');
            link.href = getDownloadUrl(sessionId);
            link.download = 'beat-reactive-video.mp4';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          }
        } else if (status.status === 'error') {
          setIsExporting(false);
          setExportStatusLabel(null);
          setError('Export failed. Please try again.');
        } else {
          setTimeout(pollExportStatus, 500);
        }
      };
      
      pollExportStatus();
    } catch (err) {
      setIsExporting(false);
      setExportStatusLabel(null);
      const errorMessage = err instanceof Error ? err.message : 'Failed to export video';
      
      // Check if this is a session/file missing error
      if (errorMessage.includes('No image uploaded') || 
          errorMessage.includes('No audio uploaded') ||
          errorMessage.includes('Session not found') ||
          errorMessage.includes('Missing image or audio')) {
        handleSessionReset();
      } else {
        setError(errorMessage);
      }
    }
  }, [sessionId, resolution, settings, effectToggles, exportAspectRatios, handleSessionReset]);
  
  const canExport = imageFile && audioFile && settings.end_time > settings.start_time && exportAspectRatios.length > 0;
  const exportButtonLabel = exportAspectRatios.length > 1
    ? `Export ${exportAspectRatios.length} formats at ${resolution}`
    : `Export at ${resolution}`;
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
          
          <div className="flex items-center gap-2">
            <a
              href="#/transform"
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-surface-600 hover:text-cyan-600 hover:bg-cyan-50 rounded-lg transition-colors"
            >
              <Wand2 className="w-4 h-4" />
              <span className="hidden sm:inline">Transform Image</span>
            </a>
            <a
              href="#/demo"
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-surface-600 hover:text-violet-600 hover:bg-violet-50 rounded-lg transition-colors"
            >
              <PlayCircle className="w-4 h-4" />
              <span className="hidden sm:inline">Effects Demo</span>
              <span className="sm:hidden">Demo</span>
            </a>
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
        
        {/* Step 3: Edit & Export */}
        {currentStep === 3 && sessionId && (
          <AudioPreviewProvider
            audioUrl={audioPreviewUrl}
            startTime={settings.start_time}
            endTime={settings.end_time}
          >
            <div className="animate-fade-in">
              <div className="text-center mb-8">
                <h2 className="font-display text-2xl font-bold text-surface-900 mb-2">
                  Edit & Export
                </h2>
                <p className="text-surface-500">
                  Adjust effects and hit Play to preview instantly — export when ready
                </p>
              </div>

              <div className="grid lg:grid-cols-3 gap-8 items-start">
                <div className="lg:col-span-2 space-y-6 lg:sticky lg:top-6 lg:z-10 lg:max-h-[calc(100dvh-1.5rem)] lg:overflow-y-auto">
                  {imagePreview && (
                    <LivePreviewCanvas
                      imageUrl={imagePreview}
                      aspectRatio={settings.aspect_ratio}
                      effectToggles={effectToggles}
                      audioFeatures={audioAnalysis}
                      imageAnalysis={imageAnalysis}
                      isLoading={isLoadingAnalysis || isAnalyzing}
                    />
                  )}

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

                <div className="space-y-6">
                  <div className="bg-white rounded-2xl border border-surface-200 p-4">
                    <span className="text-sm font-medium text-surface-700 block mb-1">Preview Aspect Ratio</span>
                    <p className="text-xs text-surface-500 mb-3">Controls the live preview canvas</p>
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

                  <EffectControls
                    effectToggles={effectToggles}
                    onChange={handleEffectTogglesChange}
                    onLoadPreset={handleLoadPreset}
                    onAutoSuggest={handleAutoSuggest}
                    isAutoSuggesting={isAutoSuggesting}
                    imageAnalysis={imageAnalysis}
                  />

                  <RenderSettings
                    aspectRatio={settings.aspect_ratio}
                    resolution={resolution}
                    onAspectRatioChange={handleAspectRatioChange}
                    onResolutionChange={handleResolutionChange}
                    compact
                    showAspectRatio={false}
                  />

                  <div className="bg-white rounded-2xl border border-surface-200 p-4">
                    <span className="text-sm font-medium text-surface-700 block mb-1">Export Formats</span>
                    <p className="text-xs text-surface-500 mb-3">Select one or more aspect ratios to export</p>
                    <div className="space-y-2">
                      {ASPECT_RATIOS.map((ratio) => {
                        const isSelected = exportAspectRatios.includes(ratio.value);
                        return (
                          <label
                            key={ratio.value}
                            className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
                              isSelected
                                ? 'bg-accent/10 border border-accent/30'
                                : 'bg-surface-50 border border-transparent hover:bg-surface-100'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => handleExportAspectRatioToggle(ratio.value)}
                              className="w-4 h-4 rounded border-surface-300 text-accent focus:ring-accent/50"
                            />
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium text-surface-700">{ratio.label}</div>
                              <div className="text-xs text-surface-500">{ratio.description}</div>
                            </div>
                          </label>
                        );
                      })}
                    </div>
                  </div>

                  <button
                    onClick={handleExport}
                    disabled={!canExport || isExporting}
                    className="w-full py-4 bg-gradient-to-r from-violet-500 to-purple-600 text-white font-medium rounded-xl hover:from-violet-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-purple-500/20 flex items-center justify-center gap-2"
                  >
                    {isExporting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        {exportStatusLabel ?? `Exporting at ${resolution}...`}
                      </>
                    ) : (
                      <>
                        <Download className="w-4 h-4" />
                        {exportButtonLabel}
                      </>
                    )}
                  </button>

                  {isExporting && (
                    <div className="h-2 bg-surface-200 rounded-full overflow-hidden">
                      <div
                        className="h-full progress-bar rounded-full"
                        style={{ width: `${exportProgress}%` }}
                      />
                    </div>
                  )}
                </div>
              </div>
            </div>
          </AudioPreviewProvider>
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

// Router component
export default function App() {
  const [route, setRoute] = useState(parseHash);

  // Listen for hash changes
  useEffect(() => {
    const handleHashChange = () => {
      setRoute(parseHash());
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigateHome = useCallback(() => {
    window.location.hash = '';
    setRoute({ page: 'main' });
  }, []);

  const navigateToVideo = useCallback((sessionId: string) => {
    window.location.hash = `/video/${sessionId}`;
    setRoute({ page: 'main', sessionId });
  }, []);

  if (route.page === 'demo') {
    return (
      <DemoPage 
        initialEffect={route.effectKey} 
        onNavigateHome={navigateHome}
      />
    );
  }

  if (route.page === 'transform') {
    return (
      <TransformPage
        onNavigateToVideo={navigateToVideo}
        onNavigateHome={navigateHome}
      />
    );
  }

  return <MainApp initialSessionId={route.sessionId} />;
}
