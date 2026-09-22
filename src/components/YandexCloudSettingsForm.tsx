import { useState, useEffect } from 'react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000';

interface YandexCloudSettings {
  folder_id?: string;
  bucket_name?: string;
  endpoint?: string;
  access_key_id?: string;
  secret_access_key?: string;
  service_account_key?: string;
}

export default function YandexCloudSettingsForm() {
  const [settings, setSettings] = useState<YandexCloudSettings>({
    folder_id: '',
    bucket_name: '',
    endpoint: 'https://storage.yandexcloud.net',
    access_key_id: '',
    secret_access_key: '',
    service_account_key: '',
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  // Загрузка текущих настроек при монтировании
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/yandex-cloud/settings`);
      if (response.ok) {
        const data = await response.json();
        setSettings({
          folder_id: data.folder_id || '',
          bucket_name: data.bucket_name || '',
          endpoint: data.endpoint || 'https://storage.yandexcloud.net',
          access_key_id: data.access_key_id || '',
          secret_access_key: '', // Не загружаем секретный ключ из соображений безопасности
          service_account_key: data.service_account_key ? '***загружен***' : '',
        });
        setMessage({ type: 'success', text: 'Настройки загружены' });
      }
    } catch (error) {
      console.error('Ошибка загрузки настроек:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      const payload: YandexCloudSettings = { ...settings };
      
      // Если ключ не менялся, не отправляем его
      if (settings.service_account_key === '***загружен***') {
        delete payload.service_account_key;
      }

      const response = await fetch(`${BACKEND_URL}/yandex-cloud/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({ type: 'success', text: 'Настройки успешно сохранены!' });
        loadSettings(); // Перезагружаем, чтобы обновить статус
      } else {
        setMessage({ type: 'error', text: `Ошибка: ${data.detail || 'Неизвестная ошибка'}` });
      }
    } catch (error) {
      setMessage({ type: 'error', text: `Ошибка подключения: ${error}` });
    } finally {
      setLoading(false);
    }
  };

  const handleJsonKeyUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const json = JSON.parse(event.target?.result as string);
        setSettings(prev => ({
          ...prev,
          service_account_key: JSON.stringify(json, null, 2),
        }));
        setMessage({ type: 'success', text: 'JSON-ключ загружен' });
      } catch (error) {
        setMessage({ type: 'error', text: 'Неверный формат JSON-ключа' });
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8">
      <h2 className="text-2xl font-bold mb-6 text-white">⚙️ Настройки Яндекс Облака</h2>
      
      {message && (
        <div className={`mb-6 p-4 rounded-lg ${
          message.type === 'success' 
            ? 'bg-green-500/20 border border-green-500/50 text-green-200' 
            : 'bg-red-500/20 border border-red-500/50 text-red-200'
        }`}>
          {message.text}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* JSON-ключ сервисного аккаунта */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            🔑 JSON-ключ сервисного аккаунта
          </label>
          <div className="space-y-2">
            {settings.service_account_key && settings.service_account_key !== '***загружен***' && (
              <div className="bg-green-500/20 border border-green-500/50 rounded px-3 py-2 text-sm text-green-200">
                ✅ Ключ загружен
              </div>
            )}
            {settings.service_account_key === '***загружен***' && (
              <div className="bg-blue-500/20 border border-blue-500/50 rounded px-3 py-2 text-sm text-blue-200">
                💾 Ключ уже сохранён в БД (оставьте пустым, если не нужно менять)
              </div>
            )}
            <input
              type="file"
              accept=".json"
              onChange={handleJsonKeyUpload}
              className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"
            />
            <textarea
              value={settings.service_account_key && settings.service_account_key !== '***загружен***' ? settings.service_account_key : ''}
              onChange={(e) => setSettings(prev => ({ ...prev, service_account_key: e.target.value }))}
              placeholder="Или вставьте JSON-ключ вручную..."
              rows={8}
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-xs"
            />
          </div>
          <p className="mt-2 text-xs text-gray-400">
            Создайте ключ в консоли Яндекс Облака: Service Account → Keys → Create New Key → JSON
          </p>
        </div>

        {/* Folder ID */}
        <div>
          <label htmlFor="folderId" className="block text-sm font-medium text-gray-300 mb-2">
            📁 Folder ID (для SpeechKit)
          </label>
          <input
            type="text"
            id="folderId"
            value={settings.folder_id}
            onChange={(e) => setSettings(prev => ({ ...prev, folder_id: e.target.value }))}
            placeholder="b1g..."
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Bucket Name */}
        <div>
          <label htmlFor="bucketName" className="block text-sm font-medium text-gray-300 mb-2">
            🪣 Имя бакета (Object Storage)
          </label>
          <input
            type="text"
            id="bucketName"
            value={settings.bucket_name}
            onChange={(e) => setSettings(prev => ({ ...prev, bucket_name: e.target.value }))}
            placeholder="my-bucket"
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Endpoint */}
        <div>
          <label htmlFor="endpoint" className="block text-sm font-medium text-gray-300 mb-2">
            🌐 S3 Endpoint
          </label>
          <input
            type="text"
            id="endpoint"
            value={settings.endpoint}
            onChange={(e) => setSettings(prev => ({ ...prev, endpoint: e.target.value }))}
            placeholder="https://storage.yandexcloud.net"
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Access Key ID */}
        <div>
          <label htmlFor="accessKeyId" className="block text-sm font-medium text-gray-300 mb-2">
            🔑 Access Key ID
          </label>
          <input
            type="text"
            id="accessKeyId"
            value={settings.access_key_id}
            onChange={(e) => setSettings(prev => ({ ...prev, access_key_id: e.target.value }))}
            placeholder="YCA..."
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Secret Access Key */}
        <div>
          <label htmlFor="secretAccessKey" className="block text-sm font-medium text-gray-300 mb-2">
            🔒 Secret Access Key
          </label>
          <input
            type="password"
            id="secretAccessKey"
            value={settings.secret_access_key}
            onChange={(e) => setSettings(prev => ({ ...prev, secret_access_key: e.target.value }))}
            placeholder="Введите секретный ключ"
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="mt-2 text-xs text-gray-400">
            Ключ не отображается из соображений безопасности после сохранения
          </p>
        </div>

        {/* Кнопки действий */}
        <div className="flex gap-4 pt-4">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <i className="fas fa-spinner fa-spin"></i>
                Сохранение...
              </>
            ) : (
              <>
                <i className="fas fa-save"></i>
                Сохранить настройки
              </>
            )}
          </button>
          
          <button
            type="button"
            onClick={loadSettings}
            className="px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white font-semibold rounded-lg transition-colors"
          >
            <i className="fas fa-redo"></i>
          </button>
        </div>
      </form>

      {/* Быстрые действия */}
      <div className="mt-8 pt-8 border-t border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">🚀 Быстрые действия</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={async () => {
              try {
                const response = await fetch(`${BACKEND_URL}/yandex-cloud/iam-token`, { method: 'POST' });
                const data = await response.json();
                if (response.ok) {
                  alert(`✅ IAM токен получен!\nСрок действия: ${new Date(data.expires_at).toLocaleString()}`);
                } else {
                  alert(`❌ Ошибка: ${data.detail}`);
                }
              } catch (error) {
                alert(`Ошибка: ${error}`);
              }
            }}
            className="px-4 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <i className="fas fa-key"></i>
            Получить IAM токен
          </button>
          
          <button
            onClick={async () => {
              try {
                const response = await fetch(`${BACKEND_URL}/yandex-cloud/test-connection`, { method: 'POST' });
                const data = await response.json();
                if (response.ok) {
                  alert(`✅ ${data.message}`);
                } else {
                  alert(`❌ Ошибка: ${data.detail}`);
                }
              } catch (error) {
                alert(`Ошибка: ${error}`);
              }
            }}
            className="px-4 py-3 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <i className="fas fa-check-circle"></i>
            Проверить подключение
          </button>
        </div>
      </div>
    </div>
  );
}
