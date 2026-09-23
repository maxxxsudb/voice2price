import React, { useState } from 'react';
import { Cloud as CloudIcon, Folder, Database, CheckCircle, AlertTriangle, Eye, EyeOff, Save, KeyRound } from 'lucide-react';
import { YandexCloudConfig } from '../types';

interface YandexCloudSettingsProps {
  config: YandexCloudConfig;
  onUpdate: (config: YandexCloudConfig) => void;
}

const API_BASE = '/api/yandex-cloud';

const YandexCloudSettings: React.FC<YandexCloudSettingsProps> = ({ config, onUpdate }) => {
  const [apiKey, setApiKey] = useState(config.apiKey || '');
  const [folderId, setFolderId] = useState(config.folderId || '');
  const [bucketName, setBucketName] = useState(config.bucketName || '');
  const [accessKeyId, setAccessKeyId] = useState(config.accessKeyId || '');
  const [secretAccessKey, setSecretAccessKey] = useState(config.secretAccessKey || '');
  const [showApiKey, setShowApiKey] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<{ success?: boolean; message?: string } | null>(null);

  const isApiKeyValid = apiKey.trim().length > 10;
  const isFolderIdValid = folderId.startsWith('b1g') && folderId.length >= 12;
  const isBucketConfigured = bucketName.trim() !== '';
  const canSave = apiKey.trim() !== '' && folderId.trim() !== '' && bucketName.trim() !== ''
    && accessKeyId.trim() !== '' && secretAccessKey.trim() !== '';

  const handleSaveAndTest = async () => {
    if (!apiKey.trim()) { setTestResult({ success: false, message: 'Введите API-ключ сервисного аккаунта (AQVN...)' }); return; }
    if (!folderId.trim()) { setTestResult({ success: false, message: 'Введите Folder ID' }); return; }
    if (!bucketName.trim()) { setTestResult({ success: false, message: 'Введите имя бакета Object Storage' }); return; }
    if (!accessKeyId.trim() || !secretAccessKey.trim()) {
      setTestResult({ success: false, message: 'Введите Access Key ID и Secret Access Key (IAM → сервисный аккаунт → Ключи доступа)' });
      return;
    }

    setSaving(true);
    setTestResult(null);

    try {
      // 1. Сохраняем настройки в БД
      const newConfig: YandexCloudConfig = { apiKey, folderId, bucketName, accessKeyId, secretAccessKey };
      const saveResponse = await fetch(`${API_BASE}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig),
      });

      if (!saveResponse.ok) {
        const saveError = await saveResponse.json().catch(() => ({}));
        throw new Error(saveError.error || `Ошибка сохранения настроек (${saveResponse.status})`);
      }

      onUpdate(newConfig);

      // 2. Проверяем подключение: тестовая загрузка объекта в бакет
      const testResponse = await fetch(`${API_BASE}/test-connection`, { method: 'POST' });
      const testData = await testResponse.json().catch(() => ({}));

      if (testResponse.ok && testData.success) {
        setTestResult({
          success: true,
          message: '✅ Настройки сохранены в БД. Тестовая загрузка в Object Storage прошла успешно.',
        });
      } else {
        setTestResult({
          success: false,
          message: `⚠️ Настройки сохранены, но проверка подключения не прошла: ${testData.error || testData.message || 'Неизвестная ошибка'}`,
        });
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: `❌ Ошибка: ${error instanceof Error ? error.message : 'Неизвестная ошибка'}`,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-blue-900 flex items-center gap-2">
          <CloudIcon className="w-5 h-5" />
          Настройки Яндекс Облака
        </h3>
        <p className="text-blue-700 mt-2 text-sm">
          Ровно 5 параметров — как в рабочем сценарии распознавания SpeechKit через Object Storage.
          Всё сохраняется в базу данных.
        </p>
      </div>

      {/* API-ключ */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-900">
          <span className="inline-flex items-center gap-1"><KeyRound className="w-4 h-4 text-gray-500" /></span>
          {' '}API-ключ сервисного аккаунта <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <input
            type={showApiKey ? 'text' : 'password'}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="AQVN..."
            className={`w-full px-3 py-2 pr-10 border rounded-md text-gray-900 placeholder-gray-400 ${
              apiKey && !isApiKeyValid
                ? 'border-red-300 bg-red-50'
                : isApiKeyValid
                ? 'border-green-300 bg-green-50'
                : 'border-gray-300 bg-white'
            } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
          />
          <button
            type="button"
            onClick={() => setShowApiKey(!showApiKey)}
            className="absolute right-2 top-2 p-1 text-gray-600 hover:text-gray-900"
          >
            {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        <p className="text-gray-600 text-xs">
          IAM → Сервисный аккаунт → <code className="bg-gray-100 px-1 rounded text-gray-900">API-ключ</code>. Нужны роли{' '}
          <code className="bg-gray-100 px-1 rounded text-gray-900">ai.speechkit-stt.user</code> и{' '}
          <code className="bg-gray-100 px-1 rounded text-gray-900">storage.uploader</code>.
        </p>
        {isApiKeyValid && (
          <p className="text-green-700 text-xs flex items-center gap-1 font-medium">
            <CheckCircle className="w-3 h-3" /> API-ключ заполнен
          </p>
        )}
      </div>

      {/* Folder ID */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-900">
          Folder ID <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <input
            type="text"
            value={folderId}
            onChange={(e) => setFolderId(e.target.value)}
            placeholder="b1gbre1u8o8khnnig1fn"
            className={`w-full px-3 py-2 pl-10 border rounded-md text-gray-900 placeholder-gray-400 ${
              folderId && !isFolderIdValid
                ? 'border-red-300 bg-red-50'
                : isFolderIdValid
                ? 'border-green-300 bg-green-50'
                : 'border-gray-300 bg-white'
            } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
          />
          <Folder className="w-4 h-4 absolute left-3 top-3 text-gray-500" />
        </div>
        {folderId && !isFolderIdValid && (
          <p className="text-red-700 text-xs flex items-center gap-1 font-medium">
            <AlertTriangle className="w-3 h-3" />
            Folder ID должен начинаться с "b1g"
          </p>
        )}
        {isFolderIdValid && (
          <p className="text-green-700 text-xs flex items-center gap-1 font-medium">
            <CheckCircle className="w-3 h-3" />
            Folder ID валиден
          </p>
        )}
      </div>

      {/* Object Storage */}
      <div className="border-t pt-6 space-y-4">
        <h4 className="font-medium text-gray-900 flex items-center gap-2">
          <Database className="w-4 h-4" />
          Object Storage (обязательно — файлы загружаются в бакет)
        </h4>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-900">
            Имя бакета <span className="text-red-500">*</span>
          </label>
          <div className="relative">
            <input
              type="text"
              value={bucketName}
              onChange={(e) => setBucketName(e.target.value)}
              placeholder="speech-file"
              className={`w-full px-3 py-2 pl-10 border rounded-md text-gray-900 placeholder-gray-400 ${
                isBucketConfigured ? 'border-green-300 bg-green-50' : 'border-gray-300 bg-white'
              } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
            />
            <Database className="w-4 h-4 absolute left-3 top-3 text-gray-500" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-900">
              Access Key ID <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={accessKeyId}
              onChange={(e) => setAccessKeyId(e.target.value)}
              placeholder="YCAJE..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 placeholder-gray-400 bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-900">
              Secret Access Key <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <input
                type={showSecret ? 'text' : 'password'}
                value={secretAccessKey}
                onChange={(e) => setSecretAccessKey(e.target.value)}
                placeholder="YCONF..."
                className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md text-gray-900 placeholder-gray-400 bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                type="button"
                onClick={() => setShowSecret(!showSecret)}
                className="absolute right-2 top-2 p-1 text-gray-600 hover:text-gray-900"
              >
                {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
        <p className="text-gray-600 text-xs">
          Статические S3-ключи: IAM → сервисный аккаунт → «Создать ключ доступа» (аксесс-ключ и секретный ключ).
        </p>
      </div>

      {/* Кнопка сохранения */}
      <div className="flex gap-3 pt-4">
        <button
          onClick={handleSaveAndTest}
          disabled={saving || !canSave}
          className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition-colors flex items-center justify-center gap-2"
        >
          {saving ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Сохранение...
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              Сохранить в БД и проверить подключение
            </>
          )}
        </button>
      </div>

      {/* Результат */}
      {testResult && (
        <div
          className={`p-4 rounded-md border ${
            testResult.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
          }`}
        >
          <div className="flex items-start gap-3">
            {testResult.success ? (
              <CheckCircle className="w-5 h-5 text-green-700 mt-0.5" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-red-700 mt-0.5" />
            )}
            <div className="flex-1">
              <p className={`font-medium ${testResult.success ? 'text-green-900' : 'text-red-900'}`}>
                {testResult.success ? 'Успешно!' : 'Ошибка'}
              </p>
              <p className={`text-sm mt-1 ${testResult.success ? 'text-green-700' : 'text-red-700'}`}>
                {testResult.message}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Инструкция */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mt-6">
        <h4 className="font-medium text-gray-900 mb-2">Как получить реквизиты:</h4>
        <ol className="list-decimal list-inside space-y-1 text-sm text-gray-900">
          <li>Зайдите в <a href="https://console.cloud.yandex.ru/" target="_blank" rel="noopener noreferrer" className="text-blue-700 underline hover:text-blue-900">консоль Яндекс Облака</a></li>
          <li>IAM → Сервисные аккаунты → выберите аккаунт (роли: ai.speechkit-stt.user, storage.uploader)</li>
          <li>«Создать API-ключ» → скопируйте значение (AQVN...) в поле «API-ключ»</li>
          <li>«Создать ключ доступа» → Access Key ID (YCAJE...) и Secret Access Key (YCONF...)</li>
          <li>Object Storage → создайте/выберите бакет, укажите его имя</li>
          <li>Folder ID — из раздела «Каталоги» (начинается с b1g)</li>
        </ol>
      </div>
    </div>
  );
};

export default YandexCloudSettings;
