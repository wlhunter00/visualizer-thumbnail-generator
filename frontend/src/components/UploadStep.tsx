import { useCallback, useState, ReactNode } from 'react';
import { Upload, Check, Loader2 } from 'lucide-react';

interface UploadStepProps {
  type: 'image' | 'audio';
  file: File | null;
  preview?: string | null;
  duration?: number;
  onUpload: (file: File) => void;
  active: boolean;
  loading?: boolean;
  icon: ReactNode;
}

export default function UploadStep({
  type,
  file,
  preview,
  duration,
  onUpload,
  active,
  loading = false,
  icon,
}: UploadStepProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  
  const acceptTypes = type === 'image'
    ? 'image/jpeg,image/png,image/webp,image/gif'
    : 'audio/mpeg,audio/wav,audio/mp3,audio/flac,audio/ogg';
  
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);
  
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);
  
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      onUpload(droppedFile);
    }
  }, [onUpload]);
  
  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      onUpload(selectedFile);
    }
  }, [onUpload]);
  
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };
  
  return (
    <div
      className={`relative bg-white rounded-2xl border-2 border-dashed transition-all ${
        file
          ? 'border-accent bg-accent/5'
          : isDragOver
          ? 'border-accent bg-accent/5'
          : active
          ? 'border-surface-300'
          : 'border-surface-200'
      }`}
    >
      <input
        type="file"
        accept={acceptTypes}
        onChange={handleFileSelect}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        disabled={loading}
      />
      
      <div className="p-8 flex flex-col items-center text-center">
        {loading ? (
          <>
            <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-4">
              <Loader2 className="w-8 h-8 text-accent animate-spin" />
            </div>
            <p className="font-medium text-surface-700 mb-1">
              {type === 'image' ? 'Uploading image...' : 'Processing audio...'}
            </p>
            <p className="text-sm text-surface-400">
              This may take a moment
            </p>
          </>
        ) : file ? (
          <>
            {type === 'image' && preview ? (
              <div className="w-24 h-24 rounded-xl overflow-hidden mb-4 shadow-lg">
                <img src={preview} alt="Preview" className="w-full h-full object-cover" />
              </div>
            ) : (
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-4">
                <Check className="w-8 h-8 text-accent" />
              </div>
            )}
            <p className="font-medium text-surface-900 truncate max-w-full">
              {file.name}
            </p>
            {type === 'audio' && duration !== undefined && duration > 0 && (
              <p className="text-sm text-surface-500 mt-1">
                {formatDuration(duration)}
              </p>
            )}
            <p className="text-xs text-surface-400 mt-2">
              Click or drag to replace
            </p>
          </>
        ) : (
          <>
            <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 ${
              active ? 'bg-accent/10 text-accent' : 'bg-surface-100 text-surface-400'
            }`}>
              {icon}
            </div>
            <p className="font-medium text-surface-700 mb-1">
              {type === 'image' ? 'Drop your cover art here' : 'Drop your audio file here'}
            </p>
            <p className="text-sm text-surface-400 mb-4">
              or click to browse
            </p>
            <div className="flex items-center gap-2 text-surface-400">
              <Upload className="w-4 h-4" />
              <span className="text-xs">
                {type === 'image' ? 'JPG, PNG, WebP, GIF' : 'MP3, WAV, FLAC, OGG'}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

