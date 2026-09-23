import { useState } from 'react';
import type { ApiConfig } from '../types';

interface Props {
  config: ApiConfig;
  onChange: (config: ApiConfig) => void;
}

export default function ApiSettings({ config, onChange }: Props) {
  const [saved, setSaved] = useState(false);

  const handleChange = (newConfig: ApiConfig) => {
    onChange(newConfig);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="bg-blue-500/10 border border-blue-500/20 rounded-2xl p-6">
        <h3 className="text-blue-300 font-semibold flex items-center gap-2 mb-2">
          <i className="fas fa-info-circle"></i>
          Как получить API ключ
        </h3>
        <ol className="text-blue-200/80 text-sm space-y-1 list-decimal list-inside">
          <li>Перейдите на <a href="https://console.cloud.yandex.ru/" target="_blank" rel="noopener noreferrer" className="underline hover:text-blue-200">console.cloud.yandex.ru</a></li>
          <li>Создайте сервисный аккаунт с ролью <code className="bg-blue-500/20 px-1 rounded">editor</code></li>
          <li>Создайте API-ключ для сервисного аккаунта</li>
        </ol>
      </div>

      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6 space-y-5">
        <div className="flex items-center justify-between">
          <h3 className="text-white font-semibold text-lg flex items-center gap-2">
            <i className="fas fa-key text-yellow-400"></i>
            Настройки Яндекс SpeechKit
          </h3>
          {saved && (
            <span className="text-green-400 text-sm flex items-center gap-1">
              <i className="fas fa-check-circle"></i>
              Сохранено
            </span>
          )}
        </div>
        
        <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-3">
          <p className="text-green-300/80 text-xs flex items-start gap-2">
            <i className="fas fa-save mt-0.5"></i>
            <span>
              <strong>Автосохранение:</strong> Настройки автоматически сохраняются в браузере и будут доступны после перезагрузки страницы.
            </span>
          </p>
        </div>

        <div>
          <label className="block text-sm text-gray-300 mb-2">API ключ</label>
          <input
            type="password"
            value={config.apiKey}
            onChange={(e) => handleChange({ ...config, apiKey: e.target.value })}
            placeholder="Введите API ключ..."
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-yellow-400/50 focus:ring-1 focus:ring-yellow-400/50 transition-all"
          />
        </div>

        <div>
          <label className="block text-sm text-gray-300 mb-2">Folder ID (опционально)</label>
          <input
            type="text"
            value={config.folderId}
            onChange={(e) => handleChange({ ...config, folderId: e.target.value })}
            placeholder="b1g..."
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-yellow-400/50 focus:ring-1 focus:ring-yellow-400/50 transition-all"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-300 mb-2">Язык</label>
            <select
              value={config.language}
              onChange={(e) => handleChange({ ...config, language: e.target.value })}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-yellow-400/50 focus:ring-1 focus:ring-yellow-400/50 transition-all"
            >
              <option value="ru-RU" className="bg-slate-800 text-white">Русский</option>
              <option value="en-US" className="bg-slate-800 text-white">Английский</option>
              <option value="tr-TR" className="bg-slate-800 text-white">Турецкий</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-2">Модель</label>
            <select
              value={config.model}
              onChange={(e) => handleChange({ ...config, model: e.target.value })}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-yellow-400/50 focus:ring-1 focus:ring-yellow-400/50 transition-all"
            >
              <option value="general" className="bg-slate-800 text-white">Общая (general)</option>
              <option value="general:rc" className="bg-slate-800 text-white">Общая RC</option>
              <option value="maps" className="bg-slate-800 text-white">Топонимы</option>
              <option value="dates" className="bg-slate-800 text-white">Даты и числа</option>
              <option value="names" className="bg-slate-800 text-white">Имена</option>
              <option value="numbers" className="bg-slate-800 text-white">Числа</option>
            </select>
          </div>
        </div>

      </div>
    </div>
  );
}
