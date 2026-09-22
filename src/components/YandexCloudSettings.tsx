import { useState } from 'react';

export interface YandexCloudConfig {
  serviceAccountKey: string; // JSON-ключ сервисного аккаунта
  folderId: string;          // Folder ID для SpeechKit
  bucketName: string;        // Имя бакета Object Storage
  accessKeyId: string;       // Access Key для Object Storage
  secretAccessKey: string;   // Secret Key для Object Storage
}

interface Props {
  config: YandexCloudConfig;
  onChange: (config: YandexCloudConfig) => void;
}

export default function YandexCloudSettings({ config, onChange }: Props) {
  const [saved, setSaved] = useState(false);
  const [showJsonKey, setShowJsonKey] = useState(false);
  
  const handleChange = (newConfig: YandexCloudConfig) => {
    onChange(newConfig);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleJsonKeyChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    try {
      // Проверяем валидность JSON
      const parsed = JSON.parse(e.target.value);
      if (parsed.service_account_id && parsed.private_key) {
        handleChange({ ...config, serviceAccountKey: e.target.value });
      } else {
        // Всё равно сохраняем, но предупреждаем
        handleChange({ ...config, serviceAccountKey: e.target.value });
      }
    } catch {
      // Не валидный JSON, но всё равно сохраняем
      handleChange({ ...config, serviceAccountKey: e.target.value });
    }
  };
  
  return (
    <div className="space-y-6">
      {/* Инструкция */}
      <div className="bg-blue-500/10 border border-blue-500/20 rounded-2xl p-6">
        <h3 className="text-blue-300 font-semibold flex items-center gap-2 mb-3">
          <i className="fas fa-info-circle"></i>
          Как настроить Яндекс Облако
        </h3>
        <ol className="text-blue-200/80 text-sm space-y-2 list-decimal list-inside">
          <li>Перейдите на <a href="https://console.cloud.yandex.ru/" target="_blank" rel="noopener noreferrer" className="underline hover:text-blue-200">console.cloud.yandex.ru</a></li>
          <li>Создайте сервисный аккаунт с ролью <code className="bg-blue-500/20 px-1 rounded">editor</code> или <code className="bg-blue-500/20 px-1 rounded">ai.languageModels.user</code></li>
          <li>Создайте статический ключ доступа (JSON) для сервисного аккаунта</li>
          <li>Скопируйте содержимое JSON-файла в поле "Приватный ключ (JSON)" ниже</li>
          <li>Укажите Folder ID (где будет использоваться SpeechKit)</li>
          <li>При необходимости настройте Object Storage (бакет, ключи доступа)</li>
        </ol>
      </div>

      {/* Основное хранилище настроек */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6 space-y-5">
        <div className="flex items-center justify-between">
          <h3 className="text-white font-semibold text-lg flex items-center gap-2">
            <i className="fab fa-yandex text-yellow-400"></i>
            Настройки Яндекс Облака
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

        {/* Приватный JSON-ключ */}
        <div>
          <label className="block text-sm text-gray-300 mb-2">
            Приватный ключ (JSON-ключ сервисного аккаунта) *
          </label>
          <div className="relative">
            <textarea
              value={config.serviceAccountKey}
              onChange={handleJsonKeyChange}
              placeholder='{"id": "...", "service_account_id": "...", "created_at": "...", "private_key": "-----BEGIN PRIVATE KEY-----..."}'
              rows={6}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white font-mono text-xs placeholder-gray-500 focus:outline-none focus:border-yellow-400/50 focus:ring-1 focus:ring-yellow-400/50 transition-all resize-y"
            />
            <button
              type="button"
              onClick={() => setShowJsonKey(!showJsonKey)}
              className="absolute top-3 right-3 text-gray-400 hover:text-white transition-colors"
              title={showJsonKey ? 'Скрыть ключ' : 'Показать ключ'}
            >
              <i className={`fas ${showJsonKey ? 'fa-eye-slash' : 'fa-eye'}`}></i>
            </button>
          </div>
          <p className="text-gray-400 text-xs mt-2 flex items-start gap-2">
            <i className="fas fa-shield-alt text-yellow-400 mt-0.5"></i>
            <span>
              Ключ хранится только в вашем браузере (localStorage). 
              Для работы через бэкенд ключ будет передаваться на сервер.
            </span>
          </p>
        </div>

        {/* Folder ID */}
        <div>
          <label className="block text-sm text-gray-300 mb-2">
            Folder ID (каталог в Яндекс Облаке) *
          </label>
          <input
            type="text"
            value={config.folderId}
            onChange={(e) => handleChange({ ...config, folderId: e.target.value })}
            placeholder="b1g..."
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-yellow-400/50 focus:ring-1 focus:ring-yellow-400/50 transition-all"
          />
          <p className="text-gray-400 text-xs mt-1">
            Используется для SpeechKit и других сервисов
          </p>
        </div>

        {/* Разделитель */}
        <div className="border-t border-white/10 pt-4">
          <h4 className="text-white font-medium mb-3 flex items-center gap-2">
            <i className="fas fa-database text-purple-400"></i>
            Object Storage (опционально)
          </h4>
          <p className="text-gray-400 text-xs mb-4">
            Настройки для работы с объектным хранилищем (загрузка больших файлов, архивы)
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-300 mb-2">Имя бакета</label>
              <input
                type="text"
                value={config.bucketName}
                onChange={(e) => handleChange({ ...config, bucketName: e.target.value })}
                placeholder="my-bucket"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-yellow-400/50 focus:ring-1 focus:ring-yellow-400/50 transition-all"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-300 mb-2">Access Key ID</label>
              <input
                type="text"
                value={config.accessKeyId}
                onChange={(e) => handleChange({ ...config, accessKeyId: e.target.value })}
                placeholder="YC..."
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-yellow-400/50 focus:ring-1 focus:ring-yellow-400/50 transition-all"
              />
            </div>
          </div>

          <div className="mt-4">
            <label className="block text-sm text-gray-300 mb-2">Secret Access Key</label>
            <input
              type="password"
              value={config.secretAccessKey}
              onChange={(e) => handleChange({ ...config, secretAccessKey: e.target.value })}
              placeholder="Введите секретный ключ..."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-yellow-400/50 focus:ring-1 focus:ring-yellow-400/50 transition-all"
            />
          </div>
        </div>

        {/* Информация о статусе */}
        <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-4">
          <h4 className="text-purple-300 font-semibold text-sm mb-2 flex items-center gap-2">
            <i className="fas fa-circle-check"></i>
            Текущий статус
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${config.serviceAccountKey ? 'bg-green-400' : 'bg-red-400'}`}></span>
              <span className="text-gray-300">
                JSON-ключ: {config.serviceAccountKey ? '✅ Настроен' : '❌ Не указан'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${config.folderId ? 'bg-green-400' : 'bg-red-400'}`}></span>
              <span className="text-gray-300">
                Folder ID: {config.folderId ? `✅ ${config.folderId}` : '❌ Не указан'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${config.bucketName ? 'bg-green-400' : 'bg-gray-400'}`}></span>
              <span className="text-gray-300">
                Object Storage: {config.bucketName ? `✅ ${config.bucketName}` : '⚪ Не настроен'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${config.accessKeyId && config.secretAccessKey ? 'bg-green-400' : 'bg-gray-400'}`}></span>
              <span className="text-gray-300">
                Ключи S3: {config.accessKeyId && config.secretAccessKey ? '✅ Настроены' : '⚪ Не указаны'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Предупреждение о безопасности */}
      <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-4">
        <p className="text-amber-300/80 text-xs flex items-start gap-2">
          <i className="fas fa-exclamation-triangle mt-0.5"></i>
          <span>
            <strong>Внимание!</strong> Никогда не передавайте JSON-ключ сервисного аккаунта третьим лицам.
            Храните его в секрете и регулярно обновляйте ключи доступа.
          </span>
        </p>
      </div>
    </div>
  );
}
