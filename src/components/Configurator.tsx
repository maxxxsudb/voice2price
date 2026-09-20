import { useState } from 'react';
import type { AppConfig } from '../types';

interface Props {
  config: AppConfig;
  onChange: (config: AppConfig) => void;
}

const PRESET_TERMS = [
  'артикул', 'серийный номер', 'модель', 'партия',
  'дата производства', 'срок годности', 'ГОСТ', 'ТУ',
  'количество', 'цена', 'наименование', 'поставщик',
  'инвентарный номер', 'штрих-код', 'сертификат',
];

export default function Configurator({ config, onChange }: Props) {
  const [termInput, setTermInput] = useState('');

  const addTerm = (term: string) => {
    const trimmed = term.trim();
    if (trimmed && !config.nomenclatureTerms.includes(trimmed)) {
      onChange({ ...config, nomenclatureTerms: [...config.nomenclatureTerms, trimmed] });
    }
  };

  const removeTerm = (term: string) => {
    onChange({ ...config, nomenclatureTerms: config.nomenclatureTerms.filter(t => t !== term) });
  };

  return (
    <div className="space-y-6">
      {/* API Settings */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <h3 className="text-white font-semibold text-lg mb-4 flex items-center gap-2">
          <i className="fas fa-key text-yellow-400"></i>
          Авторизация SpeechKit
        </h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-300 mb-1.5">
              API-ключ <span className="text-red-400">*</span>
            </label>
            <input
              type="password"
              value={config.apiKey}
              onChange={(e) => onChange({ ...config, apiKey: e.target.value })}
              placeholder="AQVN..."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-yellow-400/50 focus:ring-1 focus:ring-yellow-400/50 transition-all font-mono text-sm"
            />
            <p className="text-gray-500 text-xs mt-1">
              Получить: <a href="https://console.cloud.yandex.ru/" target="_blank" rel="noopener noreferrer" className="text-yellow-400/70 hover:text-yellow-400 underline">console.cloud.yandex.ru</a> → Сервисный аккаунт → API-ключ
            </p>
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1.5">Folder ID</label>
            <input
              type="text"
              value={config.folderId}
              onChange={(e) => onChange({ ...config, folderId: e.target.value })}
              placeholder="b1g..."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-yellow-400/50 focus:ring-1 focus:ring-yellow-400/50 transition-all font-mono text-sm"
            />
          </div>
        </div>
      </div>

      {/* Processing Settings */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <h3 className="text-white font-semibold text-lg mb-4 flex items-center gap-2">
          <i className="fas fa-gear text-cyan-400"></i>
          Параметры обработки
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-300 mb-1.5">Папка с MP3</label>
            <input
              type="text"
              value={config.audioDir}
              onChange={(e) => onChange({ ...config, audioDir: e.target.value })}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400/50 transition-all font-mono text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1.5">Папка для результатов</label>
            <input
              type="text"
              value={config.outputDir}
              onChange={(e) => onChange({ ...config, outputDir: e.target.value })}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400/50 transition-all font-mono text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1.5">Язык</label>
            <select
              value={config.language}
              onChange={(e) => onChange({ ...config, language: e.target.value })}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-cyan-400/50 transition-all"
            >
              <option value="ru-RU" className="bg-slate-800">🇷🇺 Русский</option>
              <option value="en-US" className="bg-slate-800">🇬🇧 Английский</option>
              <option value="tr-TR" className="bg-slate-800">🇹🇷 Турецкий</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1.5">Модель распознавания</label>
            <select
              value={config.model}
              onChange={(e) => onChange({ ...config, model: e.target.value })}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-cyan-400/50 transition-all"
            >
              <option value="general" className="bg-slate-800">Общая (general)</option>
              <option value="general:rc" className="bg-slate-800">Общая RC</option>
              <option value="general:deprecated" className="bg-slate-800">Устаревшая (deprecated)</option>
            </select>
          </div>
        </div>

        {/* Export options */}
        <div className="mt-4 pt-4 border-t border-white/10">
          <p className="text-sm text-gray-300 mb-3">Форматы экспорта:</p>
          <div className="flex flex-wrap gap-4">
            {[
              { key: 'exportJson' as const, label: 'JSON', icon: 'fa-file-code' },
              { key: 'exportTxt' as const, label: 'TXT', icon: 'fa-file-lines' },
              { key: 'exportCsv' as const, label: 'CSV', icon: 'fa-file-csv' },
            ].map(({ key, label, icon }) => (
              <label key={key} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config[key]}
                  onChange={(e) => onChange({ ...config, [key]: e.target.checked })}
                  className="w-4 h-4 rounded bg-white/10 border-white/20 text-yellow-400 focus:ring-yellow-400/50"
                />
                <i className={`fas ${icon} text-gray-400 text-sm`}></i>
                <span className="text-gray-300 text-sm">{label}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Nomenclature */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <h3 className="text-white font-semibold text-lg mb-4 flex items-center gap-2">
          <i className="fas fa-tags text-purple-400"></i>
          Номенклатура для поиска
        </h3>

        <p className="text-gray-400 text-sm mb-4">
          Термины, которые скрипт будет искать в распознанном тексте.
          Поддерживается нечёткий поиск (fuzzy matching) для учёта ошибок распознавания.
        </p>

        {/* Add term */}
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={termInput}
            onChange={(e) => setTermInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                addTerm(termInput);
                setTermInput('');
              }
            }}
            placeholder="Введите термин и нажмите Enter..."
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-400/50 transition-all"
          />
          <button
            onClick={() => { addTerm(termInput); setTermInput(''); }}
            className="px-5 py-3 rounded-xl bg-purple-500/20 text-purple-300 font-medium hover:bg-purple-500/30 transition-colors"
          >
            <i className="fas fa-plus mr-1"></i>
          </button>
        </div>

        {/* Current terms */}
        {config.nomenclatureTerms.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {config.nomenclatureTerms.map((term) => (
              <span
                key={term}
                className="inline-flex items-center gap-2 bg-purple-500/20 text-purple-300 text-sm px-3 py-1.5 rounded-full border border-purple-500/20"
              >
                {term}
                <button onClick={() => removeTerm(term)} className="hover:text-white transition-colors">
                  <i className="fas fa-xmark text-xs"></i>
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Presets */}
        <div className="pt-3 border-t border-white/10">
          <p className="text-gray-400 text-xs mb-2">Быстрые примеры (нажмите чтобы добавить):</p>
          <div className="flex flex-wrap gap-1.5">
            {PRESET_TERMS
              .filter(t => !config.nomenclatureTerms.includes(t))
              .map((term) => (
                <button
                  key={term}
                  onClick={() => addTerm(term)}
                  className="text-xs px-2.5 py-1 rounded-full bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white transition-colors border border-white/5"
                >
                  + {term}
                </button>
              ))}
          </div>
        </div>

        {/* Fuzzy search */}
        <div className="mt-4 pt-4 border-t border-white/10">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={config.useFuzzySearch}
              onChange={(e) => onChange({ ...config, useFuzzySearch: e.target.checked })}
              className="w-4 h-4 rounded bg-white/10 border-white/20 text-purple-400 focus:ring-purple-400/50"
            />
            <div>
              <span className="text-gray-300 text-sm font-medium">Нечёткий поиск (fuzzy matching)</span>
              <p className="text-gray-500 text-xs">
                Учитывает ошибки распознавания речи. Например, "артикула" найдёт "артикул"
              </p>
            </div>
          </label>

          {config.useFuzzySearch && (
            <div className="mt-3 ml-7">
              <label className="block text-xs text-gray-400 mb-1">
                Порог совпадения: {Math.round(config.fuzzyThreshold * 100)}%
              </label>
              <input
                type="range"
                min="0.5"
                max="1"
                step="0.05"
                value={config.fuzzyThreshold}
                onChange={(e) => onChange({ ...config, fuzzyThreshold: parseFloat(e.target.value) })}
                className="w-full accent-purple-400"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
