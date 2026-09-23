import { useState, useEffect } from 'react';
import { Cloud, Upload, FileText, Tags, Sheet, Code, Users } from 'lucide-react';
import FileUploader from './components/FileUploader';
import ApiSettings from './components/ApiSettings';
import YandexCloudSettings from './components/YandexCloudSettings';
import RecognitionResults from './components/RecognitionResults';
import PythonScriptGenerator from './components/PythonScriptGenerator';
import AudioAnalyzer from './components/AudioAnalyzer';
import NomenclatureSearch from './components/NomenclatureSearch';
import XlsxAnalyzer from './components/XlsxAnalyzer';
import EmployeesList from './components/EmployeesList';
import EmployeeDetail from './components/EmployeeDetail';
import type { AudioFile, RecognitionResult, ApiConfig, YandexCloudConfig } from './types';

// URL бэкенда — берём из переменной окружения или используем localhost
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000';

function App() {
  // Список загруженных аудиофайлов
  const [files, setFiles] = useState<AudioFile[]>([]);
  
  // Настройки API Яндекс SpeechKit (с сохранением в localStorage) - УСТАРЕЛО
  const [apiConfig, setApiConfig] = useState<ApiConfig>(() => {
    const saved = localStorage.getItem('apiConfig');
    return saved ? JSON.parse(saved) : {
      apiKey: '',
      folderId: '',
      language: 'ru-RU',
      model: 'general',
    };
  });

  // Настройки Яндекс Облака (новый способ через JSON-ключ сервисного аккаунта)
  const [yandexCloudConfig, setYandexCloudConfig] = useState<YandexCloudConfig>(() => {
    const saved = localStorage.getItem('yandexCloudConfig');
    return saved ? JSON.parse(saved) : {
      serviceAccountKey: '',
      folderId: '',
      bucketName: '',
      accessKeyId: '',
      secretAccessKey: '',
    };
  });

  // Сохранение настроек API при изменении (устаревший метод)
  const updateApiConfig = (config: ApiConfig) => {
    setApiConfig(config);
    localStorage.setItem('apiConfig', JSON.stringify(config));
    console.log('✅ [FRONTEND] Настройки API сохранены в localStorage (устаревший метод)');
  };

  // Сохранение настроек Яндекс Облака (новый метод)
  const updateYandexCloudConfig = (config: YandexCloudConfig) => {
    setYandexCloudConfig(config);
    localStorage.setItem('yandexCloudConfig', JSON.stringify(config));
    console.log('✅ [FRONTEND] Настройки Яндекс Облака сохранены в localStorage');
  };
  
  // Результаты распознавания
  const [results, setResults] = useState<RecognitionResult[]>([]);
  
  // Флаг обработки (идёт распознавание)
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Активная вкладка
  const [activeTab, setActiveTab] = useState<'upload' | 'yandex_cloud' | 'results' | 'python' | 'nomenclature' | 'xlsx' | 'employees'>('upload');
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string | null>(null);
  
  // Термины номенклатуры для поиска
  const [nomenclatureTerms, setNomenclatureTerms] = useState<string[]>([]);
  
  // Статус доступности бэкенда
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

  // Автоматическая проверка бэкенда при загрузке
  useEffect(() => {
    checkBackend();
  }, []);

  // Добавление новых файлов
  const handleFilesAdded = (newFiles: AudioFile[]) => {
    setFiles((prev) => [...prev, ...newFiles]);
  };

  // Удаление файла
  const handleFileRemove = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  // Запуск распознавания речи
  const handleRecognize = async () => {
    if (!apiConfig.apiKey || files.length === 0) return;
    setIsProcessing(true);

    // Проверяем доступность бэкенда
    const hasBackend = await checkBackend();

    const newResults: RecognitionResult[] = [];

    // Обрабатываем каждый файл
    for (const file of files) {
      try {
        if (hasBackend) {
          // === Вариант 1: Через бэкенд (рекомендуется) ===
          const formData = new FormData();
          formData.append('file', file);
          formData.append('api_key', apiConfig.apiKey);
          formData.append('folder_id', apiConfig.folderId);
          formData.append('language', apiConfig.language);
          formData.append('model', apiConfig.model);
          formData.append('nomenclature', JSON.stringify(nomenclatureTerms));

          console.log(`📤 [FRONTEND] Отправка файла ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} МБ)`);
          
          const response = await fetch(`${BACKEND_URL}/recognize`, {
            method: 'POST',
            body: formData,
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: response.statusText }));
            throw new Error(errorData.error || `Ошибка сервера: ${response.status}`);
          }

          const data = await response.json();
          
          // Проверяем использовался ли асинхронный API
          const isAsync = data.raw_response?.operation_id !== undefined;
          console.log(`✅ [FRONTEND] Распознавание завершено (${isAsync ? 'асинхронно' : 'синхронно'})`);
          
          newResults.push({
            fileId: file.id,
            fileName: file.name,
            text: data.text || '',
            confidence: data.confidence || 0,
            status: 'success',
            rawResponse: data,
          });
        } else {
          // === Вариант 2: Прямой запрос к SpeechKit (может не работать из-за CORS) ===
          const audioContext = new AudioContext({ sampleRate: 16000 });
          const arrayBuffer = await file.arrayBuffer();
          const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
          const channelData = audioBuffer.getChannelData(0);
          
          // Конвертируем в PCM 16-bit
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

  // Добавление термина номенклатуры
  const handleAddNomenclatureTerm = (term: string) => {
    if (term && !nomenclatureTerms.includes(term)) {
      setNomenclatureTerms((prev) => [...prev, term]);
    }
  };

  // Удаление термина номенклатуры
  const handleRemoveNomenclatureTerm = (term: string) => {
    setNomenclatureTerms((prev) => prev.filter((t) => t !== term));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Шапка */}
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
          
          {/* Индикатор статуса бэкенда */}
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

      {/* Предупреждение если бэкенд недоступен */}
      {backendAvailable === false && (
        <div className="max-w-7xl mx-auto px-4 pt-4">
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 text-sm text-amber-200/80 flex items-start gap-2">
            <i className="fas fa-exclamation-triangle mt-0.5 text-amber-400"></i>
            <span>
              <strong>Бэкенд не запущен.</strong> Распознавание через SpeechKit из браузера блокируется CORS.
              Запустите: <code className="bg-amber-500/20 px-1.5 rounded">python backend/server.py</code>
              {' '}— см. вкладку "Бэкенд / Скрипт" для инструкций.
            </span>
          </div>
        </div>
      )}

      {/* Навигация по вкладкам */}
      <div className="max-w-7xl mx-auto px-4 pt-6">
        <div className="flex flex-wrap gap-2 mb-6">
          {[
            { id: 'employees', label: 'Сотрудники', icon: <Users className="w-4 h-4" /> },
            { id: 'upload', label: 'Загрузка файлов', icon: <Upload className="w-4 h-4" /> },
            { id: 'yandex_cloud', label: 'Яндекс Облако', icon: <Cloud className="w-4 h-4" /> },
            { id: 'results', label: `Результаты (${results.length})`, icon: <FileText className="w-4 h-4" /> },
            { id: 'nomenclature', label: 'Номенклатура', icon: <Tags className="w-4 h-4" /> },
            { id: 'xlsx', label: 'XLSX импорт', icon: <Sheet className="w-4 h-4" /> },
            { id: 'python', label: 'Бэкенд / Скрипт', icon: <Code className="w-4 h-4" /> },
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
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Основное содержимое */}
      <main className="max-w-7xl mx-auto px-4 pb-12">
        {/* Вкладка сотрудников */}
        {activeTab === 'employees' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
              <EmployeesList 
                onSelectEmployee={setSelectedEmployeeId}
                selectedEmployeeId={selectedEmployeeId}
              />
            </div>
            <div className="lg:col-span-2">
              {selectedEmployeeId ? (
                <EmployeeDetail employeeId={selectedEmployeeId} />
              ) : (
                <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-12 text-center">
                  <i className="fas fa-user-tie text-4xl text-gray-600 mb-4"></i>
                  <p className="text-gray-400">Выберите сотрудника</p>
                  <p className="text-gray-500 text-sm mt-1">
                    Для просмотра номенклатуры, клиентов и словаря
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Вкладка загрузки файлов */}
        {activeTab === 'upload' && (
          <div className="space-y-6">
            <AudioAnalyzer />
            <FileUploader onFilesAdded={handleFilesAdded} />
            
            {/* Список загруженных файлов */}
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
                
                {/* Кнопка запуска распознавания */}
                <button
                  onClick={handleRecognize}
                  disabled={isProcessing || !apiConfig.apiKey}
                  className="mt-4 w-full py-3 rounded-xl bg-gradient-to-r from-yellow-400 to-orange-500 text-black font-bold text-sm hover:from-yellow-300 hover:to-orange-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isProcessing ? (
                    <>
                      <i className="fas fa-spinner fa-spin"></i>
                      Обработка... (большие файлы могут обрабатываться до 10 минут)
                    </>
                  ) : (
                    <>
                      <i className="fas fa-microphone-lines"></i>
                      Распознать речь ({files.length} файл(ов))
                    </>
                  )}
                </button>
                
                {/* Информация о размерах файлов */}
                {files.length > 0 && (
                  <div className="mt-3 bg-blue-500/10 border border-blue-500/20 rounded-xl p-3">
                    <p className="text-blue-300/80 text-xs flex items-start gap-2">
                      <i className="fas fa-info-circle mt-0.5"></i>
                      <span>
                        <strong>Размеры файлов:</strong>{' '}
                        {files.map(f => `${f.name} (${(f.size / 1024 / 1024).toFixed(2)} МБ)`).join(', ')}
                        {files.some(f => f.size > 1_000_000) && (
                          <span className="block mt-1">
                            ⚡ Файлы &gt; 1 МБ будут обработаны через асинхронный API (может занять до 10 минут)
                          </span>
                        )}
                      </span>
                    </p>
                  </div>
                )}
                
                {/* Подсказки */}
                {!apiConfig.apiKey && (
                  <div className="mt-3 bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-3">
                    <p className="text-yellow-300/80 text-xs flex items-start gap-2">
                      <i className="fas fa-exclamation-triangle mt-0.5"></i>
                      <span>
                        <strong>API ключ не указан.</strong> Перейдите на вкладку "Настройки API" и укажите ключ Яндекс SpeechKit.
                        <button 
                          onClick={() => setActiveTab('analyze')}
                          className="ml-2 underline hover:text-yellow-200"
                        >
                          Открыть настройки →
                        </button>
                      </span>
                    </p>
                  </div>
                )}
                
                {apiConfig.apiKey && !backendAvailable && (
                  <div className="mt-3 bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                    <p className="text-red-300/80 text-xs flex items-start gap-2">
                      <i className="fas fa-server mt-0.5"></i>
                      <span>
                        <strong>Бэкенд недоступен.</strong> Убедитесь что бэкенд запущен на {BACKEND_URL}
                      </span>
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Вкладка настроек Яндекс Облака (новый метод) */}
        {activeTab === 'yandex_cloud' && (
          <YandexCloudSettings config={yandexCloudConfig} onUpdate={updateYandexCloudConfig} />
        )}

        {/* Вкладка настроек API (устаревший метод, оставлена для обратной совместимости) */}
        {activeTab === 'analyze' && (
          <ApiSettings config={apiConfig} onChange={updateApiConfig} />
        )}

        {/* Вкладка результатов */}
        {activeTab === 'results' && (
          <RecognitionResults results={results} onClear={() => setResults([])} />
        )}

        {/* Вкладка номенклатуры */}
        {activeTab === 'nomenclature' && (
          <NomenclatureSearch
            terms={nomenclatureTerms}
            onAddTerm={handleAddNomenclatureTerm}
            onRemoveTerm={handleRemoveNomenclatureTerm}
            results={results}
          />
        )}

        {/* Вкладка анализа XLSX */}
        {activeTab === 'xlsx' && (
          <XlsxAnalyzer />
        )}

        {/* Вкладка бэкенда/скрипта */}
        {activeTab === 'python' && (
          <PythonScriptGenerator config={apiConfig} files={files} />
        )}
      </main>
    </div>
  );
}

// Форматирование длительности в мм:сс
function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default App;
