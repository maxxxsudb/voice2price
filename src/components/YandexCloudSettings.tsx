import React, { useState } from 'react';
import { Cloud as CloudIcon, Folder, Database, CheckCircle, AlertTriangle, Eye, EyeOff, Save } from 'lucide-react';
import { YandexCloudConfig } from '../types';

interface YandexCloudSettingsProps {
  config: YandexCloudConfig;
  onUpdate: (config: YandexCloudConfig) => void;
}

const YandexCloudSettings: React.FC<YandexCloudSettingsProps> = ({ config, onUpdate }) => {
  const [serviceAccountKey, setServiceAccountKey] = useState(config.serviceAccountKey || '');
  const [folderId, setFolderId] = useState(config.folderId || '');
  const [bucketName, setBucketName] = useState(config.bucketName || '');
  const [accessKeyId, setAccessKeyId] = useState(config.accessKeyId || '');
  const [secretAccessKey, setSecretAccessKey] = useState(config.secretAccessKey || '');
  const [showKey, setShowKey] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success?: boolean; message?: string; iamToken?: string } | null>(null);

  const handleSaveAndTest = async () => {
    if (!serviceAccountKey.trim()) {
      setTestResult({ success: false, message: 'Введите JSON-ключ сервисного аккаунта' });
      return;
    }
    if (!folderId.trim()) {
      setTestResult({ success: false, message: 'Введите Folder ID' });
      return;
    }

    setTesting(true);
    setTestResult(null);

    try {
      // Сначала сохраняем конфигурацию в БД через бэкенд
      const newConfig: YandexCloudConfig = {
        serviceAccountKey,
        folderId,
        bucketName,
        accessKeyId,
        secretAccessKey,
      };
      
      const saveResponse = await fetch('http://localhost:5000/api/yandex-cloud/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig),
      });

      if (!saveResponse.ok) {
        const saveError = await saveResponse.json();
        throw new Error(saveError.error || 'Ошибка сохранения настроек');
      }

      const saveData = await saveResponse.json();
      console.log('Настройки сохранены в БД:', saveData);

      // Обновляем локальное состояние (для UI)
      onUpdate(newConfig);

      // Тестируем получение IAM-токена через бэкенд с сохранёнными данными
      const testResponse = await fetch('http://localhost:5000/api/yandex-cloud/test-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ serviceAccountKey, folderId }),
      });

      const testData = await testResponse.json();

      if (testResponse.ok && testData.success) {
        setTestResult({
          success: true,
          message: `✅ Настройки сохранены в БД. IAM-токен успешно получен! Срок действия: ${testData.expiresIn || 3600} сек.`,
          iamToken: testData.iamToken,
        });
      } else {
        setTestResult({
          success: false,
          message: `⚠️ Настройки сохранены, но ошибка получения токена: ${testData.error || 'Неизвестная ошибка'}`,
        });
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: `❌ Ошибка: ${error instanceof Error ? error.message : 'Неизвестная ошибка'}`,
      });
    } finally {
      setTesting(false);
    }
  };

  const validateJsonKey = (key: string): boolean => {
    try {
      const parsed = JSON.parse(key);
      return !!(parsed.id && parsed.subject_token_type && parsed.private_key);
    } catch {
      return false;
    }
  };

  const isKeyValid = validateJsonKey(serviceAccountKey);
  const isFolderIdValid = folderId.startsWith('b1g') && folderId.length >= 12;
  const isBucketConfigured = bucketName.trim() !== '';

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-blue-900 flex items-center gap-2">
          <Cloud className="w-5 h-5" />
          Настройки Яндекс Облака
        </h3>
        <p className="text-blue-700 mt-2 text-sm">
          Используйте сервисный аккаунт для безопасной аутентификации и работы с Object Storage.
        </p>
      </div>

      {/* JSON-ключ сервисного аккаунта */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          Приватный ключ (JSON-ключ сервисного аккаунта) <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <textarea
            value={serviceAccountKey}
            onChange={(e) => setServiceAccountKey(e.target.value)}
            placeholder='{"id": "...", "subject_token_type": "...", "private_key": "..."}'
            rows={6}
            className={`w-full px-3 py-2 border rounded-md font-mono text-xs ${
              serviceAccountKey && !isKeyValid
                ? 'border-red-300 bg-red-50'
                : isKeyValid
                ? 'border-green-300 bg-green-50'
                : 'border-gray-300'
            } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
          />
          <button
            type="button"
            onClick={() => setShowKey(!showKey)}
            className="absolute right-2 top-2 p-1 text-gray-500 hover:text-gray-700"
            title={showKey ? 'Скрыть' : 'Показать'}
          >
            {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        {serviceAccountKey && !isKeyValid && (
          <p className="text-red-600 text-xs flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            Неверный формат JSON-ключа
          </p>
        )}
        {isKeyValid && (
          <p className="text-green-600 text-xs flex items-center gap-1">
            <CheckCircle className="w-3 h-3" />
            JSON-ключ валиден
          </p>
        )}
        <p className="text-gray-500 text-xs">
          Скачайте ключ в консоли Яндекс Облака: Сервисные аккаунты → Создать ключ → Создать новый ключ → JSON
        </p>
      </div>

      {/* Folder ID */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          Folder ID <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <input
            type="text"
            value={folderId}
            onChange={(e) => setFolderId(e.target.value)}
            placeholder="b1gxxxxxxxxxxxxxxxxxxx"
            className={`w-full px-3 py-2 pl-10 border rounded-md ${
              folderId && !isFolderIdValid
                ? 'border-red-300 bg-red-50'
                : isFolderIdValid
                ? 'border-green-300 bg-green-50'
                : 'border-gray-300'
            } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
          />
          <Folder className="w-4 h-4 absolute left-3 top-3 text-gray-400" />
        </div>
        {folderId && !isFolderIdValid && (
          <p className="text-red-600 text-xs flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            Folder ID должен начинаться с "b1g"
          </p>
        )}
        {isFolderIdValid && (
          <p className="text-green-600 text-xs flex items-center gap-1">
            <CheckCircle className="w-3 h-3" />
            Folder ID валиден
          </p>
        )}
        <p className="text-gray-500 text-xs">
          ID каталога, где будут создаваться ресурсы. Можно найти в консоли Яндекс Облака.
        </p>
      </div>

      {/* Object Storage (опционально) */}
      <div className="border-t pt-6 space-y-4">
        <h4 className="font-medium text-gray-900 flex items-center gap-2">
          <Database className="w-4 h-4" />
          Object Storage (необязательно)
        </h4>
        
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Имя бакета</label>
          <div className="relative">
            <input
              type="text"
              value={bucketName}
              onChange={(e) => setBucketName(e.target.value)}
              placeholder="my-bucket"
              className={`w-full px-3 py-2 pl-10 border rounded-md ${
                isBucketConfigured ? 'border-green-300 bg-green-50' : 'border-gray-300'
              } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
            />
            <Database className="w-4 h-4 absolute left-3 top-3 text-gray-400" />
          </div>
          {isBucketConfigured && (
            <p className="text-green-600 text-xs flex items-center gap-1">
              <CheckCircle className="w-3 h-3" />
              Бакет настроен
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">Access Key ID</label>
            <input
              type="text"
              value={accessKeyId}
              onChange={(e) => setAccessKeyId(e.target.value)}
              placeholder="YCAXXXXXXXXXXXXXXXXX"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">Secret Access Key</label>
            <div className="relative">
              <input
                type={showSecret ? 'text' : 'password'}
                value={secretAccessKey}
                onChange={(e) => setSecretAccessKey(e.target.value)}
                placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                type="button"
                onClick={() => setShowSecret(!showSecret)}
                className="absolute right-2 top-2.5 p-1 text-gray-500 hover:text-gray-700"
              >
                {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Кнопки действий */}
      <div className="flex gap-3 pt-4">
        <button
          onClick={handleSaveAndTest}
          disabled={testing || !serviceAccountKey || !folderId}
          className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition-colors flex items-center justify-center gap-2"
        >
          {testing ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Тестирование...
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              Сохранить и протестировать
            </>
          )}
        </button>
      </div>

      {/* Результат теста */}
      {testResult && (
        <div
          className={`p-4 rounded-md border ${
            testResult.success
              ? 'bg-green-50 border-green-200'
              : 'bg-red-50 border-red-200'
          }`}
        >
          <div className="flex items-start gap-3">
            {testResult.success ? (
              <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
            )}
            <div className="flex-1">
              <p
                className={`font-medium ${
                  testResult.success ? 'text-green-900' : 'text-red-900'
                }`}
              >
                {testResult.success ? 'Успешно!' : 'Ошибка'}
              </p>
              <p
                className={`text-sm mt-1 ${
                  testResult.success ? 'text-green-700' : 'text-red-700'
                }`}
              >
                {testResult.message}
              </p>
              {testResult.iamToken && (
                <details className="mt-2">
                  <summary className="text-xs text-green-600 cursor-pointer hover:text-green-800">
                    Показать IAM-токен
                  </summary>
                  <pre className="mt-1 p-2 bg-white rounded border border-green-200 text-xs overflow-x-auto text-gray-700">
                    {testResult.iamToken}
                  </pre>
                </details>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Инструкция */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mt-6">
        <h4 className="font-medium text-gray-900 mb-2">Как получить реквизиты:</h4>
        <ol className="list-decimal list-inside space-y-1 text-sm text-gray-700">
          <li>Зайдите в <a href="https://console.cloud.yandex.ru/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">консоль Яндекс Облака</a></li>
          <li>Перейдите в раздел "Сервисные аккаунты"</li>
          <li>Создайте новый сервисный аккаунт или выберите существующий</li>
          <li>Нажмите "Создать новый ключ" → Выберите формат "JSON"</li>
          <li>Скачайте файл и скопируйте его содержимое в поле "Приватный ключ"</li>
          <li>Folder ID можно найти в разделе "Каталоги" (начинается с b1g)</li>
          <li>Для Object Storage: создайте бакет и ключи доступа в разделе "Object Storage"</li>
        </ol>
      </div>
    </div>
  );
};
export default YandexCloudSettings;
