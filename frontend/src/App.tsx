import { useState, useEffect, useCallback } from 'react';
import { Step, GenerateSettings, Playbook, ASPECT_RATIOS } from './types';
import { createSession, uploadImage, uploadAudio, getWaveform, generateVideo, getGenerationStatus, exportVideo, getPreviewUrl, getDownloadUrl } from './api';
import StepIndicator from './components/StepIndicator';
import UploadStep from './components/UploadStep';
import WaveformSelector from './components/WaveformSelector';
import EffectControls from './components/EffectControls';
import VideoPreview from './components/VideoPreview';
import BrandPlaybook from './components/BrandPlaybook';
import { Music, Image as ImageIcon, Sparkles } from 'lucide-react';

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
  
  // Settings state
  const [settings, setSettings] = useState<GenerateSettings>({
    start_time: 0,
    end_time: 30,
    aspect_ratio: '9:16',
    motion_intensity: 50,
    beat_reactivity: 50,
    energy_level: 50,
  });
  
  // Generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [videoReady, setVideoReady] = useState(false);
  const [playbook, setPlaybook] = useState<Playbook | null>(null);
  const [error, setError] = useState<string | null>(null);
  
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
  
  // Handle settings change
  const handleSettingsChange = useCallback((key: keyof GenerateSettings, value: number | string) => {
    setSettings(s => ({ ...s, [key]: value }));
    // Reset video when settings change
    setVideoReady(false);
  }, []);
  
  // Generate video
  const handleGenerate = useCallback(async () => {
    if (!sessionId) return;
    
    try {
      setError(null);
      setIsGenerating(true);
      setProgress(0);
      setVideoReady(false);
      
      await generateVideo(sessionId, settings);
      
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
  }, [sessionId, settings]);
  
  // Export video
  const handleExport = useCallback(async () => {
    if (!sessionId) return;
    
    try {
      setError(null);
      await exportVideo(sessionId);
      
      // Trigger download
      const link = document.createElement('a');
      link.href = getDownloadUrl(sessionId);
      link.download = 'beat-reactive-video.mp4';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export video');
    }
  }, [sessionId]);
  
  // Go back to adjust
  const handleBackToAdjust = useCallback(() => {
    setCurrentStep(3);
    setVideoReady(false);
  }, []);
  
  const canGenerate = imageFile && audioFile && settings.end_time > settings.start_time;
  const selectedDuration = settings.end_time - settings.start_time;
  
  return (
    <div className="min-h-screen bg-surface-50">
      {/* Header */}
      <header className="border-b border-surface-200 bg-white">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-display text-xl font-bold text-surface-900">Beat Visualizer</h1>
              <p className="text-sm text-surface-500">Create music videos in seconds</p>
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
            
            {imageFile && audioFile && (
              <div className="mt-8 text-center">
                <button
                  onClick={() => setCurrentStep(3)}
                  className="px-6 py-3 bg-accent text-white font-medium rounded-xl hover:bg-accent-dark transition-colors"
                >
                  Continue to Adjust
                </button>
              </div>
            )}
          </div>
        )}
        
        {/* Step 3: Adjust */}
        {currentStep === 3 && (
          <div className="animate-fade-in">
            <div className="text-center mb-8">
              <h2 className="font-display text-2xl font-bold text-surface-900 mb-2">
                Select Region & Adjust
              </h2>
              <p className="text-surface-500">
                Choose which part of your track to visualize and dial in the vibe
              </p>
            </div>
            
            <div className="grid lg:grid-cols-3 gap-8">
              {/* Left: Preview & Waveform */}
              <div className="lg:col-span-2 space-y-6">
                {/* Image Preview */}
                {imagePreview && (
                  <div className="bg-white rounded-2xl border border-surface-200 p-4">
                    <div className="aspect-video bg-surface-100 rounded-xl overflow-hidden flex items-center justify-center">
                      <img 
                        src={imagePreview} 
                        alt="Cover art preview" 
                        className="max-w-full max-h-full object-contain"
                      />
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
                        onClick={() => handleSettingsChange('aspect_ratio', ratio.value)}
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
                
                {/* Effect Sliders */}
                <EffectControls
                  motionIntensity={settings.motion_intensity}
                  beatReactivity={settings.beat_reactivity}
                  energyLevel={settings.energy_level}
                  onChange={handleSettingsChange}
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
              </div>
              
              {/* Playbook & Actions */}
              <div className="space-y-6">
                {playbook && <BrandPlaybook playbook={playbook} />}
                
                <div className="space-y-3">
                  <button
                    onClick={handleExport}
                    className="w-full py-4 bg-accent text-white font-medium rounded-xl hover:bg-accent-dark transition-colors"
                  >
                    Export Video
                  </button>
                  
                  <button
                    onClick={handleBackToAdjust}
                    className="w-full py-3 bg-white border border-surface-200 text-surface-700 font-medium rounded-xl hover:bg-surface-50 transition-colors"
                  >
                    Adjust & Re-render
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

