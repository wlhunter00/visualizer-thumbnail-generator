import {
  createContext,
  useContext,
  useRef,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from 'react';

interface AudioPreviewContextValue {
  isPlaying: boolean;
  isAudioReady: boolean;
  absoluteTime: number;
  clipTime: number;
  startTime: number;
  endTime: number;
  play: () => Promise<void>;
  pause: () => void;
  restart: () => Promise<void>;
  toggle: () => void;
  setRegion: (start: number, end: number) => void;
}

const AudioPreviewContext = createContext<AudioPreviewContextValue | null>(null);

interface AudioPreviewProviderProps {
  children: ReactNode;
  audioUrl: string | null;
  startTime: number;
  endTime: number;
}

export function AudioPreviewProvider({
  children,
  audioUrl,
  startTime,
  endTime,
}: AudioPreviewProviderProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const rafRef = useRef<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isAudioReady, setIsAudioReady] = useState(false);
  const [absoluteTime, setAbsoluteTime] = useState(startTime);

  const clipTime = Math.max(0, absoluteTime - startTime);

  const stopRaf = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  }, []);

  const tick = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || audio.paused) return;

    const time = audio.currentTime;
    setAbsoluteTime(time);

    if (time >= endTime) {
      audio.pause();
      audio.currentTime = startTime;
      setIsPlaying(false);
      setAbsoluteTime(startTime);
      stopRaf();
      return;
    }

    rafRef.current = requestAnimationFrame(tick);
  }, [endTime, startTime, stopRaf]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !audioUrl) return;

    setIsAudioReady(false);
    audio.src = audioUrl;
    audio.load();

    const onCanPlay = () => setIsAudioReady(true);
    const onError = () => setIsAudioReady(false);
    const onEnded = () => {
      setIsPlaying(false);
      setAbsoluteTime(startTime);
      stopRaf();
    };

    audio.addEventListener('canplay', onCanPlay);
    audio.addEventListener('error', onError);
    audio.addEventListener('ended', onEnded);

    return () => {
      audio.removeEventListener('canplay', onCanPlay);
      audio.removeEventListener('error', onError);
      audio.removeEventListener('ended', onEnded);
    };
  }, [audioUrl, startTime, stopRaf]);

  useEffect(() => {
    if (isPlaying) {
      rafRef.current = requestAnimationFrame(tick);
    } else {
      stopRaf();
    }
    return stopRaf;
  }, [isPlaying, tick, stopRaf]);

  const play = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio || !audioUrl) return;
    if (audio.currentTime < startTime || audio.currentTime >= endTime) {
      audio.currentTime = startTime;
    }
    setAbsoluteTime(audio.currentTime);
    await audio.play();
    setIsPlaying(true);
  }, [audioUrl, startTime, endTime]);

  const pause = useCallback(() => {
    audioRef.current?.pause();
    setIsPlaying(false);
    stopRaf();
  }, [stopRaf]);

  const restart = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = startTime;
    setAbsoluteTime(startTime);
    await audio.play();
    setIsPlaying(true);
  }, [startTime]);

  const toggle = useCallback(() => {
    if (isPlaying) pause();
    else play();
  }, [isPlaying, pause, play]);

  const setRegion = useCallback((start: number, _end: number) => {
    setAbsoluteTime(start);
    if (audioRef.current) {
      audioRef.current.currentTime = start;
    }
    setIsPlaying(false);
    stopRaf();
  }, [stopRaf]);

  return (
    <AudioPreviewContext.Provider
      value={{
        isPlaying,
        isAudioReady,
        absoluteTime,
        clipTime,
        startTime,
        endTime,
        play,
        pause,
        restart,
        toggle,
        setRegion,
      }}
    >
      {audioUrl && <audio ref={audioRef} preload="auto" className="hidden" />}
      {children}
    </AudioPreviewContext.Provider>
  );
}

export function useAudioPreview() {
  const ctx = useContext(AudioPreviewContext);
  if (!ctx) throw new Error('useAudioPreview must be used within AudioPreviewProvider');
  return ctx;
}

export function useOptionalAudioPreview() {
  return useContext(AudioPreviewContext);
}
