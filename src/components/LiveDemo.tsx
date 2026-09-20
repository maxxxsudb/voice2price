import { useRef, useState, useCallback } from 'react';
import type { AudioFileInfo } from '../types';

export default function LiveDemo() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [fileInfo, setFileInfo] = useState<AudioFileInfo | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const analyzeAudio = useCallback(async (file: File) => {
    setIsAnalyzing(true);

    try {
      const audioContext = new AudioContext();
      const arrayBuffer = await file.arrayBuffer();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

      setFileInfo({
        name: file.name,
        size: file.size,
        duration: audioBuffer.duration,
        sampleRate: audioBuffer.sampleRate,
        channels: audioBuffer.numberOfChannels,
      });

      drawWaveform(audioBuffer);
      audioContext.close();
    } catch (err) {
      console.error('Error analyzing audio:', err);
    }

    setIsAnalyzing(false);
  }, []);

  const drawWaveform = (audioBuffer: AudioBuffer) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
    ctx.fillRect(0, 0, width, height);

    const channelData = audioBuffer.getChannelData(0);
    const step = Math.ceil(channelData.length / width);

    // Draw waveform bars
    const gradient = ctx.createLinearGradient(0, 0, width, 0);
    gradient.addColorStop(0, '#a855f7');
    gradient.addColorStop(0.5, '#f59e0b');
    gradient.addColorStop(1, '#22c55e');

    for (let i = 0; i < width; i++) {
      let min = 1.0;
      let max = -1.0;

      for (let j = 0; j < step; j++) {
        const datum = channelData[i * step + j] || 0;
        if (datum < min) min = datum;
        if (datum > max) max = datum;
      }

      const yMin = ((1 + min) * height) / 2;
      const yMax = ((1 + max) * height) / 2;

      ctx.fillStyle = gradient;
      ctx.fillRect(i, yMin, 1, yMax - yMin || 1);
    }

    // Center line
    ctx.beginPath();
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      analyzeAudio(file);
    }
  };

  return (
    <div className="space-y-6">
      {/* Explanation */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <h2 className="text-white font-bold text-lg mb-3 flex items-center gap-2">
          <i className="fas fa-play text-green-400"></i>
          Демо: анализ аудио прямо в браузере
        </h2>
        <p className="text-gray-300 text-sm mb-4">
          Здесь можно загрузить MP3 файл и посмотреть его параметры — waveform, длительность,
          частоту дискретизации. Это работает полностью в браузере, без отправки данных на сервер.
        </p>
        <p className="text-gray-400 text-xs">
          ⚠️ Распознавание речи (SpeechKit) из браузера не работает из-за CORS-политик Яндекса.
          Для распознавания используйте Python-скрипт (вкладка "Python скрипт").
        </p>
      </div>

      {/* Upload */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <input
          ref={inputRef}
          type="file"
          accept="audio/*"
          onChange={handleFileChange}
          className="hidden"
        />

        <button
          onClick={() => inputRef.current?.click()}
          className="w-full py-4 rounded-xl bg-gradient-to-r from-purple-500/20 to-cyan-500/20 border border-purple-500/30 text-white font-medium hover:from-purple-500/30 hover:to-cyan-500/30 transition-all flex items-center justify-center gap-3"
        >
          <i className="fas fa-file-audio text-2xl text-purple-400"></i>
          <span>Выбрать MP3 файл для анализа</span>
        </button>

        {/* Waveform */}
        <div className="mt-4 bg-black/30 rounded-xl overflow-hidden border border-white/5">
          <canvas ref={canvasRef} className="w-full h-[120px]" />
        </div>

        {/* Info */}
        {fileInfo && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-gray-400 text-xs">Файл</p>
              <p className="text-white font-medium text-sm truncate">{fileInfo.name}</p>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-gray-400 text-xs">Длительность</p>
              <p className="text-white font-semibold">
                {Math.floor(fileInfo.duration! / 60)}:{String(Math.floor(fileInfo.duration! % 60)).padStart(2, '0')}
              </p>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-gray-400 text-xs">Sample Rate</p>
              <p className="text-white font-semibold">{(fileInfo.sampleRate! / 1000).toFixed(1)} кГц</p>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-gray-400 text-xs">Размер</p>
              <p className="text-white font-semibold">{(fileInfo.size / 1024 / 1024).toFixed(1)} МБ</p>
            </div>
          </div>
        )}

        {isAnalyzing && (
          <div className="mt-4 text-center text-gray-400 text-sm">
            <i className="fas fa-spinner fa-spin mr-2"></i>
            Анализ аудио...
          </div>
        )}
      </div>

      {/* Architecture */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <i className="fas fa-diagram-project text-yellow-400"></i>
          Архитектура решения
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-4">
            <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center mb-2">
              <i className="fas fa-laptop text-purple-400"></i>
            </div>
            <h4 className="text-white font-medium text-sm mb-1">Ваш компьютер</h4>
            <p className="text-gray-400 text-xs">
              Python-скрипт читает MP3, конвертирует в PCM, отправляет на распознавание
            </p>
          </div>
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4">
            <div className="w-8 h-8 rounded-lg bg-yellow-500/20 flex items-center justify-center mb-2">
              <i className="fas fa-cloud text-yellow-400"></i>
            </div>
            <h4 className="text-white font-medium text-sm mb-1">Яндекс SpeechKit</h4>
            <p className="text-gray-400 text-xs">
              Облачный API распознавания речи. Принимает PCM 16kHz, возвращает текст
            </p>
          </div>
          <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4">
            <div className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center mb-2">
              <i className="fas fa-file-export text-green-400"></i>
            </div>
            <h4 className="text-white font-medium text-sm mb-1">Результаты</h4>
            <p className="text-gray-400 text-xs">
              JSON, TXT, CSV файлы с распознанным текстом и найденной номенклатурой
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
