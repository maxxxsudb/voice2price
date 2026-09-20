import { useState } from 'react';
import FileUploader from './components/FileUploader';
import ApiSettings from './components/ApiSettings';
import RecognitionResults from './components/RecognitionResults';
import PythonScriptGenerator from './components/PythonScriptGenerator';
import AudioAnalyzer from './components/AudioAnalyzer';
import NomenclatureSearch from './components/NomenclatureSearch';
import type { AudioFile, RecognitionResult, ApiConfig } from './types';

// URL бэкенда (Flask сервер)
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000';

function App() {
  const [files, setFiles] = useState<AudioFile[]>([]);
  const [apiConfig, setApiConfig] = useState<ApiConfig>({
    apiKey: '',
    folderId: '',
    language: 'ru-RU',
    model: 'general',
  });
  const [results, setResults] = useState<RecognitionResult[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState<'upload' | 'analyze' | 'results' | 'python' | 'nomenclature'>('upload');
  const [nomenclatureTerms, setNomenclatureTerms] = useState<string[]>([]);
  const [backendAvailable, setBackendAvailable] = useState<boolean | null>(null);

  // Проверка доступности бэкенда
  const checkBackend = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/health`, { method: 'GET' });
      setBackendAvailable(response.ok);
      return response.ok;
    } catch {
      setBackendAvailable(false);
      return false;
    }
  };

  const handleFilesAdded = (newFiles: AudioFile[]) => {
    setFiles((prev) => [...prev, ...newFiles]);
  };

  const handleFileRemove = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleRecognize = async () => {
    if (!apiConfig.apiKey || files.length === 0) return;
    setIsProcessing(true);

    // Сначала проверим бэкенд
    const hasBackend = await checkBackend();

    const newResults: RecognitionResult[] = [];

    for (const file of files) {
      try {
        if (hasBackend) {
          // Используем бэкенд
          const formData = new FormData();
          formData.append('file', file);
          formData.append('api_key', apiConfig.apiKey);
          formData.append('folder_id', apiConfig.folderId);
          formData.append('language', apiConfig.language);
          formData.append('model', apiConfig.model);
          formData.append('nomenclature', JSON.stringify(nomenclatureTerms));

          const response = await fetch(`${BACKEND_URL}/recognize`, {
            method: 'POST',
            body: formData,
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: response.statusText }));
            throw new Error(errorData.error || `Ошибка сервера: ${response.status}`);
          }

          const data = await response.json();
          newResults.push({
            fileId: file.id,
            fileName: file.name,
            text: data.text || '',
            confidence: data.confidence || 0,
            status: 'success',
            rawResponse: data,
          });
        } else {
          // Fallback: прямые запросы к SpeechKit (может не работать из-за CORS)
          const audioContext = new AudioContext({ sampleRate: 16000 });
          const arrayBuffer = await file.arrayBuffer();
          const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
          const channelData = audioBuffer.getChannelData(0);
          const pcmData = new Int16Array(channelData.length);
          for (let i = 0; i < channelData.length; i++) {
            const s = Math.max(-1, Math.min(1, channelData[i]));
            pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }

          const blob = new Blob([pcmData.buffer], { type: 'audio/l16' });
          const params = new URLSearchParams({
            topic: apiConfig.model === 'general' ? 'general' : apiConfig.model,
            lang: apiConfig.language,
            format: 'lpcm',
            sampleRateHertz: '16000',
          });

          const response = await fetch(
            `https://stt.api.cloud.yandex.net/speech/v1/stt:recognize?${params.toString()}`,
            {
              method: 'POST',
              headers: { Authorization: `Api-Key ${apiConfig.apiKey}` },
              body: blob,
            }
          );

          if (!response.ok) {
            throw new Error(`CORS/Ошибка API: ${response.status}. Запустите бэкенд.`);
          }

          const data = await response.json();
          newResults.push({
            fileId: file.id,
            fileName: file.name,
            text: data.result || '',
            confidence: data.confidence || 0,
            status: 'success',
            rawResponse: data,
          });
          audioContext.close();
        }
      } catch (error) {
        newResults.push({
          fileId: file.id,
          fileName: file.name,
          text: '',
          confidence: 0,
          status: 'error',
          error: error instanceof Error ? error.message : 'Неизвестная ошибка',
        });
      }
    }

    setResults((prev) => [...prev, ...newResults]);
    setIsProcessing(false);
    setActiveTab('results');
  };

  const handleAddNomenclatureTerm = (term: string) => {
    if (term && !nomenclatureTerms.includes(term)) {
      setNomenclatureTerms((prev) => [...prev, term]);
    }
  };

  const handleRemoveNomenclatureTerm = (term: string) => {
    setNomenclatureTerms((prev) => prev.filter((t) => t !== term));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="border-b border-white/10 backdrop-blur-sm bg-white/5">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center">
              <i className="fas fa-waveform-lines text-white text-lg"></i>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Аудио Анализатор</h1>
              <p className="text-sm text-gray-400">Распознавание речи + поиск номенклатуры</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${backendAvailable === null ? 'bg-gray-500' : backendAvailable ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span className="text-xs text-gray-400">
              {backendAvailable === null ? 'Бэкенд: ?' : backendAvailable ? 'Бэкенд: онлайн' : 'Бэкенд: оффлайн'}
            </span>
            <button
              onClick={checkBackend}
              className="text-xs text-gray-500 hover:text-white transition-colors ml-2"
              title="Проверить бэкенд"
            >
              <i className="fas fa-rotate"></i>
            </button>
          </div>
        </div>
      </header>

      {/* Backend warning */}
      {backendAvailable === false && (
        <div className="max-w-7xl mx-auto px-4 pt-4">
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 text-sm text-amber-200/80 flex items-start gap-2">
            <i className="fas fa-exclamation-triangle mt-0.5 text-amber-400"></i>
            <span>
              <strong>Бэкенд не запущен.</strong> Распознавание через SpeechKit из браузера блокируется CORS.
              Запустите: <code className="bg-amber-500/20 px-1.5 rounded">python backend/server.py</code>
              {' '}— см. вкладку "Python скрипт" для инструкций.
            </span>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto px-4 pt-6">
        <div className="flex flex-wrap gap-2 mb-6">
          {[
            { id: 'upload', label: 'Загрузка файлов', icon: 'fa-upload' },
            { id: 'analyze', label: 'Настройки API', icon: 'fa-gear' },
            { id: 'results', label: `Результаты (${results.length})`, icon: 'fa-file-lines' },
            { id: 'nomenclature', label: 'Номенклатура', icon: 'fa-tags' },
            { id: 'python', label: 'Бэкенд / Скрипт', icon: 'fa-code' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                activeTab === tab.id
                  ? 'bg-white/20 text-white shadow-lg'
                  : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
              }`}
            >
              <i className={`fas ${tab.icon}`}></i>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 pb-12">
        {activeTab === 'upload' && (
          <div className="space-y-6">
            <AudioAnalyzer />
            <FileUploader onFilesAdded={handleFilesAdded} />
            {files.length > 0 && (
              <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
                <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                  <i className="fas fa-list text-yellow-400"></i>
                  Загруженные файлы ({files.length})
                </h3>
                <div className="space-y-2">
                  {files.map((file) => (
                    <div
                      key={file.id}
                      className="flex items-center justify-between bg-white/5 rounded-lg px-4 py-3"
                    >
                      <div className="flex items-center gap-3">
                        <i className="fas fa-music text-purple-400"></i>
                        <div>
                          <p className="text-white text-sm font-medium">{file.name}</p>
                          <p className="text-gray-400 text-xs">
                            {(file.size / 1024 / 1024).toFixed(2)} МБ
                            {file.duration && ` • ${formatDuration(file.duration)}`}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleFileRemove(file.id)}
                        className="text-red-400 hover:text-red-300 transition-colors"
                      >
                        <i className="fas fa-trash"></i>
                      </button>
                    </div>
                  ))}
                </div>
                <button
                  onClick={handleRecognize}
                  disabled={isProcessing || !apiConfig.apiKey}
                  className="mt-4 w-full py-3 rounded-xl bg-gradient-to-r from-yellow-400 to-orange-500 text-black font-bold text-sm hover:from-yellow-300 hover:to-orange-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isProcessing ? (
                    <>
                      <i className="fas fa-spinner fa-spin"></i>
                      Обработка...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-microphone-lines"></i>
                      Распознать речь ({files.length} файл(ов))
                    </>
                  )}
                </button>
                {!apiConfig.apiKey && (
                  <p className="mt-2 text-yellow-400/80 text-xs text-center">
                    ⚠️ Сначала укажите API ключ в настройках
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'analyze' && (
          <ApiSettings config={apiConfig} onChange={setApiConfig} />
        )}

        {activeTab === 'results' && (
          <RecognitionResults results={results} onClear={() => setResults([])} />
        )}

        {activeTab === 'nomenclature' && (
          <NomenclatureSearch
            terms={nomenclatureTerms}
            onAddTerm={handleAddNomenclatureTerm}
            onRemoveTerm={handleRemoveNomenclatureTerm}
            results={results}
          />
        )}

        {activeTab === 'python' && (
          <PythonScriptGenerator config={apiConfig} files={files} />
        )}
      </main>
    </div>
  );
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default App;
