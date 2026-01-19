import { useRef, useState, useCallback, useEffect } from 'react';
import { Play, Pause, Volume2, Loader2 } from 'lucide-react';

interface WaveformSelectorProps {
  waveformData: [number, number][];
  duration: number;
  startTime: number;
  endTime: number;
  onRegionChange: (start: number, end: number) => void;
  audioUrl?: string;
}

export default function WaveformSelector({
  waveformData,
  duration,
  startTime,
  endTime,
  onRegionChange,
  audioUrl,
}: WaveformSelectorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isDragging, setIsDragging] = useState<'start' | 'end' | 'region' | null>(null);
  const [dragStartX, setDragStartX] = useState(0);
  const [dragStartValues, setDragStartValues] = useState({ start: 0, end: 0 });
  
  // Audio playback state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(startTime);
  const [isAudioReady, setIsAudioReady] = useState(false);
  const animationFrameRef = useRef<number | null>(null);
  
  // Handle audio element loading and events
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !audioUrl) return;
    
    // Reset ready state when URL changes
    setIsAudioReady(false);
    
    const handleCanPlay = () => {
      setIsAudioReady(true);
    };
    
    const handleLoadedData = () => {
      setIsAudioReady(true);
    };
    
    const handleError = () => {
      setIsAudioReady(false);
    };
    
    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(startTime);
    };
    
    audio.addEventListener('canplay', handleCanPlay);
    audio.addEventListener('loadeddata', handleLoadedData);
    audio.addEventListener('error', handleError);
    audio.addEventListener('ended', handleEnded);
    
    // Force load the audio
    audio.load();
    
    // If already ready
    if (audio.readyState >= 3) {
      setIsAudioReady(true);
    }
    
    return () => {
      audio.removeEventListener('canplay', handleCanPlay);
      audio.removeEventListener('loadeddata', handleLoadedData);
      audio.removeEventListener('error', handleError);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [audioUrl, startTime]);
  
  // Audio playback controls
  const playPreview = useCallback(async () => {
    if (!audioRef.current || !audioUrl) return;
    
    try {
      audioRef.current.currentTime = startTime;
      await audioRef.current.play();
      setIsPlaying(true);
      setCurrentTime(startTime);
    } catch {
      setIsPlaying(false);
    }
  }, [audioUrl, startTime]);
  
  const pausePreview = useCallback(() => {
    if (!audioRef.current) return;
    
    audioRef.current.pause();
    setIsPlaying(false);
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
  }, []);
  
  const togglePlayback = useCallback(() => {
    if (isPlaying) {
      pausePreview();
    } else {
      playPreview();
    }
  }, [isPlaying, playPreview, pausePreview]);
  
  // Update playhead position during playback
  useEffect(() => {
    if (!isPlaying || !audioRef.current) return;
    
    const updatePlayhead = () => {
      if (!audioRef.current) return;
      
      const time = audioRef.current.currentTime;
      setCurrentTime(time);
      
      // Stop at end of selected region
      if (time >= endTime) {
        audioRef.current.pause();
        setIsPlaying(false);
        setCurrentTime(startTime);
        return;
      }
      
      animationFrameRef.current = requestAnimationFrame(updatePlayhead);
    };
    
    animationFrameRef.current = requestAnimationFrame(updatePlayhead);
    
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isPlaying, endTime, startTime]);
  
  // Reset playhead when region changes
  useEffect(() => {
    if (!isPlaying) {
      setCurrentTime(startTime);
    }
  }, [startTime, isPlaying]);
  
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);
  
  const timeToPercent = useCallback((time: number) => {
    return (time / duration) * 100;
  }, [duration]);
  
  const percentToTime = useCallback((percent: number) => {
    return (percent / 100) * duration;
  }, [duration]);
  
  const getMousePercent = useCallback((e: MouseEvent | React.MouseEvent) => {
    if (!containerRef.current) return 0;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    return Math.max(0, Math.min(100, (x / rect.width) * 100));
  }, []);
  
  const handleMouseDown = useCallback((e: React.MouseEvent, handle: 'start' | 'end' | 'region') => {
    e.preventDefault();
    e.stopPropagation();
    
    setIsDragging(handle);
    setDragStartX(e.clientX);
    setDragStartValues({ start: startTime, end: endTime });
  }, [startTime, endTime]);
  
  
  useEffect(() => {
    if (!isDragging) return;
    
    let didDrag = false;
    
    const handleMouseMove = (e: MouseEvent) => {
      const dx = Math.abs(e.clientX - dragStartX);
      
      // Only count as drag if moved more than 3 pixels
      if (dx > 3) {
        if (!didDrag) {
          didDrag = true;
          // Pause playback when actually starting to drag
          if (isPlaying && audioRef.current) {
            audioRef.current.pause();
            setIsPlaying(false);
          }
        }
        
        const percent = getMousePercent(e);
        const time = percentToTime(percent);
        
        if (isDragging === 'start') {
          const newStart = Math.max(0, Math.min(time, endTime - 1));
          onRegionChange(newStart, endTime);
        } else if (isDragging === 'end') {
          const newEnd = Math.min(duration, Math.max(time, startTime + 1));
          onRegionChange(startTime, newEnd);
        } else if (isDragging === 'region') {
          if (!containerRef.current) return;
          const rect = containerRef.current.getBoundingClientRect();
          const percentDelta = ((e.clientX - dragStartX) / rect.width) * 100;
          const timeDelta = (percentDelta / 100) * duration;
          
          const regionDuration = dragStartValues.end - dragStartValues.start;
          let newStart = dragStartValues.start + timeDelta;
          let newEnd = dragStartValues.end + timeDelta;
          
          // Clamp to bounds
          if (newStart < 0) {
            newStart = 0;
            newEnd = regionDuration;
          }
          if (newEnd > duration) {
            newEnd = duration;
            newStart = duration - regionDuration;
          }
          
          onRegionChange(newStart, newEnd);
        }
      }
    };
    
    const handleMouseUp = (e: MouseEvent) => {
      // If didn't drag (was a click), play from that position
      if (!didDrag && isDragging === 'region' && audioRef.current && audioUrl && isAudioReady) {
        const percent = getMousePercent(e);
        const clickTime = percentToTime(percent);
        
        if (clickTime >= startTime && clickTime <= endTime) {
          audioRef.current.currentTime = clickTime;
          setCurrentTime(clickTime);
          audioRef.current.play().then(() => {
            setIsPlaying(true);
          }).catch(() => {
            setIsPlaying(false);
          });
        }
      }
      
      setIsDragging(null);
    };
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragStartX, dragStartValues, startTime, endTime, duration, getMousePercent, percentToTime, onRegionChange, isPlaying, audioUrl, isAudioReady]);
  
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };
  
  const startPercent = timeToPercent(startTime);
  const endPercent = timeToPercent(endTime);
  
  // Render waveform bars
  const renderWaveform = () => {
    const numBars = 100;
    const step = Math.max(1, Math.floor(waveformData.length / numBars));
    
    return (
      <div className="absolute inset-0 flex items-center justify-around px-1">
        {Array.from({ length: numBars }).map((_, i) => {
          const dataIndex = Math.min(i * step, waveformData.length - 1);
          const amplitude = waveformData[dataIndex]?.[1] ?? 0.3;
          const height = Math.max(8, amplitude * 100);
          const percent = (i / numBars) * 100;
          const isInRegion = percent >= startPercent && percent <= endPercent;
          
          return (
            <div
              key={i}
              className={`w-0.5 rounded-full transition-colors ${
                isInRegion ? 'bg-accent' : 'bg-surface-300'
              }`}
              style={{ height: `${height}%` }}
            />
          );
        })}
      </div>
    );
  };
  
  const playheadPercent = timeToPercent(currentTime);
  
  return (
    <div className="space-y-3">
      {/* Hidden audio element */}
      {audioUrl && (
        <audio 
          ref={audioRef} 
          src={audioUrl} 
          preload="auto"
        />
      )}
      
      <div
        ref={containerRef}
        className="waveform-container h-24 relative cursor-pointer select-none"
      >
        {/* Waveform visualization */}
        {renderWaveform()}
        
        {/* Inactive regions (dimmed) */}
        <div
          className="absolute inset-y-0 left-0 bg-white/70 pointer-events-none"
          style={{ width: `${startPercent}%` }}
        />
        <div
          className="absolute inset-y-0 right-0 bg-white/70 pointer-events-none"
          style={{ width: `${100 - endPercent}%` }}
        />
        
        {/* Selected region overlay */}
        <div
          className="absolute inset-y-0 bg-accent/10 border-y-2 border-accent/30 cursor-move"
          style={{
            left: `${startPercent}%`,
            width: `${endPercent - startPercent}%`,
          }}
          onMouseDown={(e) => handleMouseDown(e, 'region')}
        />
        
        {/* Playhead indicator */}
        {audioUrl && (
          <div
            className="absolute inset-y-0 w-0.5 bg-red-500 pointer-events-none z-10 transition-none"
            style={{ 
              left: `${playheadPercent}%`,
              boxShadow: '0 0 4px rgba(239, 68, 68, 0.5)'
            }}
          >
            {/* Playhead top marker */}
            <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-red-500 rounded-full" />
          </div>
        )}
        
        {/* Start handle */}
        <div
          className="absolute inset-y-0 w-3 bg-accent rounded-l cursor-ew-resize flex items-center justify-center hover:bg-accent-dark transition-colors"
          style={{ left: `calc(${startPercent}% - 6px)` }}
          onMouseDown={(e) => handleMouseDown(e, 'start')}
        >
          <div className="w-0.5 h-8 bg-white/50 rounded-full" />
        </div>
        
        {/* End handle */}
        <div
          className="absolute inset-y-0 w-3 bg-accent rounded-r cursor-ew-resize flex items-center justify-center hover:bg-accent-dark transition-colors"
          style={{ left: `calc(${endPercent}% - 6px)` }}
          onMouseDown={(e) => handleMouseDown(e, 'end')}
        >
          <div className="w-0.5 h-8 bg-white/50 rounded-full" />
        </div>
      </div>
      
      {/* Controls row: Time labels + Play button */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-surface-500">{formatTime(startTime)}</span>
        
        {/* Play/Pause button */}
        {audioUrl && (
          <button
            onClick={togglePlayback}
            disabled={!isAudioReady}
            className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-dark text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {!isAudioReady ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm font-medium">Loading...</span>
              </>
            ) : isPlaying ? (
              <>
                <Pause className="w-4 h-4" />
                <span className="text-sm font-medium">Pause</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                <span className="text-sm font-medium">Preview</span>
              </>
            )}
          </button>
        )}
        
        <div className="flex items-center gap-3">
          <span className="text-xs text-accent font-medium flex items-center gap-1">
            <Volume2 className="w-3 h-3" />
            {formatTime(endTime - startTime)}
          </span>
          <span className="text-xs text-surface-500">{formatTime(endTime)}</span>
        </div>
      </div>
    </div>
  );
}

