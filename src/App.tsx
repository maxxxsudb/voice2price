import { useState } from 'react';
import Configurator from './components/Configurator';
import ScriptPreview from './components/ScriptPreview';
import Instructions from './components/Instructions';
import LiveDemo from './components/LiveDemo';
import type { AppConfig } from './types';

const DEFAULT_CONFIG: AppConfig = {
  apiKey: '',
  folderId: '',
  audioDir: './audio_files',
  language: 'ru-RU',
  model: 'general',
  nomenclatureTerms: [],
  outputDir: './output',
  useFuzzySearch: true,
  fuzzyThreshold: 0.8,
  exportJson: true,
  exportTxt: true,
  exportCsv: true,
};

function App() {
  const [config, setConfig] = useState<AppConfig>(DEFAULT_CONFIG);
  const [activeTab, setActiveTab] = useState<'demo' | 'config' | 'script' | 'instructions'>('demo');

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="border-b border-white/10 backdrop-blur-sm bg-white/5">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center">
              <i className="fas fa-microphone-lines text-white text-lg"></i>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">MP3 → Текст → Номенклатура</h1>
              <p className="text-sm text-gray-400">
                Конфигуратор Python-скрипта для Яндекс SpeechKit
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* What is this? */}
      <div className="max-w-7xl mx-auto px-4 pt-4">
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 text-sm text-amber-200/80 flex items-start gap-2">
          <i className="fas fa-lightbulb mt-0.5 text-amber-400"></i>
          <span>
            <strong>Как это работает:</strong> Это веб-страница — конфигуратор. Вы настраиваете параметры,
            а на выходе получаете готовый <code className="bg-amber-500/20 px-1 rounded">.py</code> файл,
            который запускаете у себя на компьютере. Браузер не отправляет ваши файлы никуда —
            вся обработка происходит локально через Python.
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-4 pt-4">
        <div className="flex flex-wrap gap-2 mb-6">
          {[
            { id: 'demo', label: 'Демо (браузер)', icon: 'fa-play' },
            { id: 'config', label: 'Настройки', icon: 'fa-sliders' },
            { id: 'script', label: 'Python скрипт', icon: 'fa-code' },
            { id: 'instructions', label: 'Инструкция', icon: 'fa-book' },
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

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 pb-12">
        {activeTab === 'demo' && <LiveDemo />}
        {activeTab === 'config' && <Configurator config={config} onChange={setConfig} />}
        {activeTab === 'script' && <ScriptPreview config={config} />}
        {activeTab === 'instructions' && <Instructions />}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 py-4 text-center text-gray-500 text-xs">
        <p>Яндекс SpeechKit • Python 3.8+ • ffmpeg</p>
      </footer>
    </div>
  );
}

export default App;
