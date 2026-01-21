import { useRef, useState, useEffect, useCallback } from 'react';
import { Play, Pause, RotateCcw } from 'lucide-react';

interface VideoPreviewProps {
  videoUrl: string;
  aspectRatio: string;
}

export default function VideoPreview({ videoUrl, aspectRatio }: VideoPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  
  const handlePlayPause = useCallback(() => {
    if (!videoRef.current) return;
    
    // Use video element's paused state to avoid stale closure
    if (videoRef.current.paused) {
      videoRef.current.play();
    } else {
      videoRef.current.pause();
    }
  }, []);
  
  // Spacebar keyboard handler for play/pause
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle spacebar, and ignore if user is typing in an input
      if (e.code === 'Space' && !['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) {
        e.preventDefault();
        handlePlayPause();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handlePlayPause]);
  
  const handleRestart = () => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = 0;
    videoRef.current.play();
    setIsPlaying(true);
  };
  
  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    setCurrentTime(videoRef.current.currentTime);
  };
  
  const handleLoadedMetadata = () => {
    if (!videoRef.current) return;
    setDuration(videoRef.current.duration);
  };
  
  const handleEnded = () => {
    setIsPlaying(false);
  };
  
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };
  
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;
  
  // Calculate container aspect ratio class
  const getAspectClass = () => {
    switch (aspectRatio) {
      case '9:16': return 'aspect-[9/16] max-h-[500px]';
      case '1:1': return 'aspect-square max-h-[400px]';
      case '16:9': return 'aspect-video max-h-[400px]';
      case '4:5': return 'aspect-[4/5] max-h-[450px]';
      default: return 'aspect-video';
    }
  };
  
  return (
    <div className="bg-white rounded-2xl border border-surface-200 p-4">
      <div className="flex justify-center mb-4">
        <div 
          ref={containerRef}
          className={`relative bg-black rounded-xl overflow-hidden cursor-pointer ${getAspectClass()}`}
          onClick={handlePlayPause}
        >
          <video
            ref={videoRef}
            src={videoUrl}
            className="w-full h-full object-contain pointer-events-none"
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onEnded={handleEnded}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            playsInline
          />
          
          {/* Play overlay when paused */}
          {!isPlaying && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/30 hover:bg-black/40 transition-colors">
              <div className="w-16 h-16 rounded-full bg-white/90 flex items-center justify-center">
                <Play className="w-8 h-8 text-surface-900 ml-1" />
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Controls */}
      <div className="space-y-3">
        {/* Progress bar */}
        <div className="h-1.5 bg-surface-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-accent rounded-full transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
        
        {/* Control buttons */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-surface-500">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>
          
          <div className="flex items-center gap-2">
            <button
              onClick={handleRestart}
              className="p-2 rounded-lg hover:bg-surface-100 transition-colors text-surface-500 hover:text-surface-700"
              title="Restart"
            >
              <RotateCcw className="w-5 h-5" />
            </button>
            
            <button
              onClick={handlePlayPause}
              className="p-2 rounded-lg bg-accent text-white hover:bg-accent-dark transition-colors"
            >
              {isPlaying ? (
                <Pause className="w-5 h-5" />
              ) : (
                <Play className="w-5 h-5 ml-0.5" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

