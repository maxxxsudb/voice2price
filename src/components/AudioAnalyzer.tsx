import { useRef, useState, useCallback, useEffect } from 'react';

export default function AudioAnalyzer() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [audioInfo, setAudioInfo] = useState<{
    duration: number;
    sampleRate: number;
    channels: number;
  } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const analyzeAudio = useCallback(async (file: File) => {
    setIsAnalyzing(true);
    
    try {
      const audioContext = new AudioContext();
      const arrayBuffer = await file.arrayBuffer();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      
      setAudioInfo({
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
    
    ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    ctx.fillRect(0, 0, width, height);
    
    const channelData = audioBuffer.getChannelData(0);
    const step = Math.ceil(channelData.length / width);
    
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
      
      const yMin = (1 + min) * height / 2;
      const yMax = (1 + max) * height / 2;
      
      ctx.fillStyle = gradient;
      ctx.fillRect(i, yMin, 1, yMax - yMin || 1);
    }
    
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

  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas) {
      canvas.width = canvas.offsetWidth * 2;
      canvas.height = 200;
    }
  }, []);

  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
      <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
        <i className="fas fa-wave-square text-cyan-400"></i>
        Предварительный анализ аудиофайла
      </h3>
      
      <div className="space-y-4">
        <input
          ref={inputRef}
          type="file"
          accept="audio/*"
          onChange={handleFileChange}
          className="hidden"
        />
        
        <button
          onClick={() => inputRef.current?.click()}
          className="w-full py-3 rounded-xl bg-cyan-500/20 text-cyan-300 font-medium hover:bg-cyan-500/30 transition-colors flex items-center justify-center gap-2"
        >
          <i className="fas fa-file-audio"></i>
          Выбрать файл для анализа (только просмотр, без отправки)
        </button>

        <div className="bg-black/30 rounded-xl overflow-hidden">
          <canvas ref={canvasRef} className="w-full h-[100px]" />
        </div>

        {audioInfo && (
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-gray-400 text-xs">Длительность</p>
              <p className="text-white font-semibold">{audioInfo.duration.toFixed(1)}с</p>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-gray-400 text-xs">Sample Rate</p>
              <p className="text-white font-semibold">{(audioInfo.sampleRate / 1000).toFixed(1)} кГц</p>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-gray-400 text-xs">Каналы</p>
              <p className="text-white font-semibold">{audioInfo.channels}</p>
            </div>
          </div>
        )}

        {isAnalyzing && (
          <div className="text-center text-gray-400 text-sm">
            <i className="fas fa-spinner fa-spin mr-2"></i>
            Анализ...
          </div>
        )}
      </div>
    </div>
  );
}
