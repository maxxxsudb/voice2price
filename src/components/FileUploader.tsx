import { useCallback, useRef, useState } from 'react';
import type { AudioFile } from '../types';

interface Props {
  onFilesAdded: (files: AudioFile[]) => void;
}

export default function FileUploader({ onFilesAdded }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const processFiles = useCallback(async (fileList: FileList | File[]) => {
    const audioFiles: AudioFile[] = [];
    
    for (const file of Array.from(fileList)) {
      if (!file.type.startsWith('audio/') && !file.name.match(/\.(mp3|wav|ogg|m4a|flac|aac)$/i)) {
        continue;
      }

      // Get duration
      let duration: number | undefined;
      try {
        const audioContext = new AudioContext();
        const arrayBuffer = await file.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        duration = audioBuffer.duration;
        audioContext.close();
      } catch {
        // Duration detection failed, continue without it
      }

      const audioFile = Object.assign(file, {
        id: `${file.name}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        duration,
      }) as AudioFile;

      audioFiles.push(audioFile);
    }

    if (audioFiles.length > 0) {
      onFilesAdded(audioFiles);
    }
  }, [onFilesAdded]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    processFiles(e.dataTransfer.files);
  }, [processFiles]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      processFiles(e.target.files);
      e.target.value = '';
    }
  }, [processFiles]);

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={() => inputRef.current?.click()}
      className={`relative cursor-pointer rounded-2xl border-2 border-dashed p-12 text-center transition-all ${
        isDragging
          ? 'border-yellow-400 bg-yellow-400/10'
          : 'border-white/20 bg-white/5 hover:border-white/40 hover:bg-white/10'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="audio/*,.mp3,.wav,.ogg,.m4a,.flac,.aac"
        multiple
        onChange={handleInputChange}
        className="hidden"
      />
      <div className="space-y-4">
        <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-br from-yellow-400/20 to-orange-500/20 flex items-center justify-center">
          <i className="fas fa-cloud-arrow-up text-3xl text-yellow-400"></i>
        </div>
        <div>
          <p className="text-white font-semibold text-lg">
            Перетащите аудиофайлы сюда
          </p>
          <p className="text-gray-400 text-sm mt-1">
            или нажмите для выбора • MP3, WAV, OGG, M4A, FLAC, AAC
          </p>
        </div>
        <div className="flex items-center justify-center gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <i className="fas fa-music"></i> MP3
          </span>
          <span className="flex items-center gap-1">
            <i className="fas fa-music"></i> WAV
          </span>
          <span className="flex items-center gap-1">
            <i className="fas fa-music"></i> OGG
          </span>
          <span className="flex items-center gap-1">
            <i className="fas fa-music"></i> FLAC
          </span>
        </div>
      </div>
    </div>
  );
}
