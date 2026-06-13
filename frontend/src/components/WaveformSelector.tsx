import { useRef, useState, useCallback, useEffect } from 'react';
import { Play, Pause, Volume2, Loader2 } from 'lucide-react';
import { useOptionalAudioPreview } from '../context/AudioPreviewContext';

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
  const sharedAudio = useOptionalAudioPreview();

  const [isDragging, setIsDragging] = useState<'start' | 'end' | 'region' | null>(null);
  const [dragStartX, setDragStartX] = useState(0);
  const [dragStartValues, setDragStartValues] = useState({ start: 0, end: 0 });

  // Local fallback when not inside AudioPreviewProvider
  const [localPlaying, setLocalPlaying] = useState(false);
  const [localTime, setLocalTime] = useState(startTime);
  const [localReady, setLocalReady] = useState(false);
  const animationFrameRef = useRef<number | null>(null);

  const isPlaying = sharedAudio?.isPlaying ?? localPlaying;
  const currentTime = sharedAudio?.absoluteTime ?? localTime;
  const isAudioReady = sharedAudio?.isAudioReady ?? localReady;

  useEffect(() => {
    if (sharedAudio || !audioRef.current || !audioUrl) return;
    const audio = audioRef.current;
    setLocalReady(false);
    const onReady = () => setLocalReady(true);
    const onError = () => setLocalReady(false);
    audio.addEventListener('canplay', onReady);
    audio.addEventListener('loadeddata', onReady);
    audio.addEventListener('error', onError);
    audio.load();
    return () => {
      audio.removeEventListener('canplay', onReady);
      audio.removeEventListener('loadeddata', onReady);
      audio.removeEventListener('error', onError);
    };
  }, [audioUrl, sharedAudio]);

  const playPreview = useCallback(async () => {
    if (sharedAudio) {
      await sharedAudio.play();
      return;
    }
    if (!audioRef.current || !audioUrl) return;
    try {
      audioRef.current.currentTime = startTime;
      await audioRef.current.play();
      setLocalPlaying(true);
      setLocalTime(startTime);
    } catch {
      setLocalPlaying(false);
    }
  }, [sharedAudio, audioUrl, startTime]);

  const pausePreview = useCallback(() => {
    if (sharedAudio) {
      sharedAudio.pause();
      return;
    }
    audioRef.current?.pause();
    setLocalPlaying(false);
    if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
  }, [sharedAudio]);

  const togglePlayback = useCallback(() => {
    if (isPlaying) pausePreview();
    else playPreview();
  }, [isPlaying, playPreview, pausePreview]);

  useEffect(() => {
    if (sharedAudio || !localPlaying || !audioRef.current) return;
    const updatePlayhead = () => {
      if (!audioRef.current) return;
      const time = audioRef.current.currentTime;
      setLocalTime(time);
      if (time >= endTime) {
        audioRef.current.pause();
        setLocalPlaying(false);
        setLocalTime(startTime);
        return;
      }
      animationFrameRef.current = requestAnimationFrame(updatePlayhead);
    };
    animationFrameRef.current = requestAnimationFrame(updatePlayhead);
    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [localPlaying, endTime, startTime, sharedAudio]);

  useEffect(() => {
    if (!isPlaying && !sharedAudio) setLocalTime(startTime);
  }, [startTime, isPlaying, sharedAudio]);

  const timeToPercent = useCallback((time: number) => (time / duration) * 100, [duration]);
  const percentToTime = useCallback((percent: number) => (percent / 100) * duration, [duration]);

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
      if (dx > 3) {
        if (!didDrag) {
          didDrag = true;
          pausePreview();
        }
        const percent = getMousePercent(e);
        const time = percentToTime(percent);
        if (isDragging === 'start') {
          onRegionChange(Math.max(0, Math.min(time, endTime - 1)), endTime);
        } else if (isDragging === 'end') {
          onRegionChange(startTime, Math.min(duration, Math.max(time, startTime + 1)));
        } else if (isDragging === 'region') {
          if (!containerRef.current) return;
          const rect = containerRef.current.getBoundingClientRect();
          const timeDelta = ((e.clientX - dragStartX) / rect.width) * duration;
          const regionDuration = dragStartValues.end - dragStartValues.start;
          let newStart = dragStartValues.start + timeDelta;
          let newEnd = dragStartValues.end + timeDelta;
          if (newStart < 0) { newStart = 0; newEnd = regionDuration; }
          if (newEnd > duration) { newEnd = duration; newStart = duration - regionDuration; }
          onRegionChange(newStart, newEnd);
        }
      }
    };

    const handleMouseUp = () => setIsDragging(null);
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragStartX, dragStartValues, startTime, endTime, duration, getMousePercent, percentToTime, onRegionChange, pausePreview]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const startPercent = timeToPercent(startTime);
  const endPercent = timeToPercent(endTime);
  const playheadPercent = timeToPercent(currentTime);

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
              className={`w-0.5 rounded-full transition-colors ${isInRegion ? 'bg-accent' : 'bg-surface-300'}`}
              style={{ height: `${height}%` }}
            />
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-3">
      {!sharedAudio && audioUrl && (
        <audio ref={audioRef} src={audioUrl} preload="auto" className="hidden" />
      )}

      <div ref={containerRef} className="waveform-container h-24 relative cursor-pointer select-none">
        {renderWaveform()}
        <div className="absolute inset-y-0 left-0 bg-white/70 pointer-events-none" style={{ width: `${startPercent}%` }} />
        <div className="absolute inset-y-0 right-0 bg-white/70 pointer-events-none" style={{ width: `${100 - endPercent}%` }} />
        <div
          className="absolute inset-y-0 bg-accent/10 border-y-2 border-accent/30 cursor-move"
          style={{ left: `${startPercent}%`, width: `${endPercent - startPercent}%` }}
          onMouseDown={(e) => handleMouseDown(e, 'region')}
        />
        {audioUrl && (
          <div
            className="absolute inset-y-0 w-0.5 bg-red-500 pointer-events-none z-10"
            style={{ left: `${playheadPercent}%`, boxShadow: '0 0 4px rgba(239, 68, 68, 0.5)' }}
          >
            <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-red-500 rounded-full" />
          </div>
        )}
        <div
          className="absolute inset-y-0 w-3 bg-accent rounded-l cursor-ew-resize flex items-center justify-center hover:bg-accent-dark transition-colors"
          style={{ left: `calc(${startPercent}% - 6px)` }}
          onMouseDown={(e) => handleMouseDown(e, 'start')}
        >
          <div className="w-0.5 h-8 bg-white/50 rounded-full" />
        </div>
        <div
          className="absolute inset-y-0 w-3 bg-accent rounded-r cursor-ew-resize flex items-center justify-center hover:bg-accent-dark transition-colors"
          style={{ left: `calc(${endPercent}% - 6px)` }}
          onMouseDown={(e) => handleMouseDown(e, 'end')}
        >
          <div className="w-0.5 h-8 bg-white/50 rounded-full" />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-surface-500">{formatTime(startTime)}</span>
        {audioUrl && (
          <button
            onClick={togglePlayback}
            disabled={!isAudioReady}
            className="flex items-center gap-2 px-4 py-2 bg-surface-100 hover:bg-surface-200 text-surface-700 rounded-lg transition-colors disabled:opacity-50"
          >
            {!isAudioReady ? (
              <><Loader2 className="w-4 h-4 animate-spin" /><span className="text-sm">Loading...</span></>
            ) : isPlaying ? (
              <><Pause className="w-4 h-4" /><span className="text-sm">Pause</span></>
            ) : (
              <><Play className="w-4 h-4" /><span className="text-sm">Preview Audio</span></>
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
