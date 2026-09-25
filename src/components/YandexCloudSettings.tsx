import React, { useState, useEffect } from 'react';
import { Cloud as CloudIcon, Database, CheckCircle, AlertTriangle, Eye, EyeOff, Save, KeyRound, BrainCircuit, Mic, Loader2 } from 'lucide-react';
import { YandexCloudConfig, DEFAULT_ORDER_PROMPT } from '../types';
import { cloudConfigFromSettings } from '../api';

interface YandexCloudSettingsProps {
  config: YandexCloudConfig;
  onUpdate: (config: YandexCloudConfig) => void;
}

const API_BASE = '/api/yandex-cloud';

const YANDEX_MODELS = [
  { value: 'yandexgpt-lite', label: 'yandexgpt-lite — быстрая и дешёвая' },
  { value: 'yandexgpt', label: 'yandexgpt — баланс качества и скорости' },
  { value: 'yandexgpt-pro', label: 'yandexgpt-pro — максимальное качество' },
];

type Service = 'speechkit' | 'yandexgpt';
type Check = { success: boolean; message: string } | 'running' | undefined;

// Поля ввода — белые с тёмным текстом во всех состояниях (UI_CONTRAST_REQUIREMENTS.md)
const INPUT = 'w-full px-3 py-2 border rounded-lg text-gray-900 placeholder-gray-500 bg-white border-gray-300 '
  + 'focus:ring-2 focus:ring-cyan-400 focus:border-transparent';

function Field({ label, hint, children }: { label: React.ReactNode; hint?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-gray-100">{label}</label>
      {children}
      {hint && <p className="text-gray-300 text-xs">{hint}</p>}
    </div>
  );
}

function SecretInput({ value, onChange, saved, placeholder }: {
  value: string; onChange: (v: string) => void; saved?: boolean; placeholder: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input type={show ? 'text' : 'password'} value={value} onChange={e => onChange(e.target.value)}
        placeholder={saved ? 'Сохранён в БД; введите новый для замены' : placeholder}
        className={`${INPUT} pr-10`} />
      <button type="button" onClick={() => setShow(!show)} aria-label={show ? 'Скрыть' : 'Показать'}
        className="absolute right-2 top-2 p-1 text-gray-600 hover:text-gray-900">
        {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
      </button>
    </div>
  );
}

function Status({ ready, missing }: { ready: boolean; missing: string[] }) {
  return ready
    ? <span className="rounded-full bg-emerald-300 px-2.5 py-0.5 text-xs font-medium text-slate-950">Готово</span>
    : <span className="rounded-full bg-amber-300 px-2.5 py-0.5 text-xs font-medium text-slate-950"
        title={`Не заполнено: ${missing.join(', ')}`}>Не заполнено: {missing.length}</span>;
}

function CheckResult({ check }: { check: Check }) {
  if (!check || check === 'running') return null;
  return (
    <p className={`mt-3 text-sm flex items-start gap-2 ${check.success ? 'text-emerald-300' : 'text-amber-200'}`}>
      {check.success ? <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" /> : <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />}
      <span className="break-all">{check.message}</span>
    </p>
  );
}

const YandexCloudSettings: React.FC<YandexCloudSettingsProps> = ({ config, onUpdate }) => {
  const [apiKey, setApiKey] = useState('');
  const [folderId, setFolderId] = useState(config.folderId || '');
  const [bucketName, setBucketName] = useState(config.bucketName || '');
  const [accessKeyId, setAccessKeyId] = useState(config.accessKeyId || '');
  const [secretAccessKey, setSecretAccessKey] = useState('');
  const [orderPrompt, setOrderPrompt] = useState(config.orderPrompt || DEFAULT_ORDER_PROMPT);
  const [yandexModel, setYandexModel] = useState(config.yandexModel || 'yandexgpt');
  const [saving, setSaving] = useState(false);
  const [saveResult, setSaveResult] = useState<{ success: boolean; message: string } | null>(null);
  const [checks, setChecks] = useState<Record<Service, Check>>({ speechkit: undefined, yandexgpt: undefined });

  useEffect(() => {
    setFolderId(config.folderId || '');
    setBucketName(config.bucketName || '');
    setAccessKeyId(config.accessKeyId || '');
    setOrderPrompt(config.orderPrompt || DEFAULT_ORDER_PROMPT);
    setYandexModel(config.yandexModel || 'yandexgpt');
    setApiKey('');
    setSecretAccessKey('');
  }, [config]);

  const hasKey = Boolean(apiKey.trim() || config.hasApiKey);
  const folderValid = /^b1g\w{6,}$/.test(folderId.trim());
  const common = [!hasKey && 'API-ключ', !folderId.trim() && 'Folder ID'].filter(Boolean) as string[];
  const speechkitMissing = [...common, !bucketName.trim() && 'бакет', !accessKeyId.trim() && 'Access Key ID',
    !(secretAccessKey.trim() || config.hasSecretAccessKey) && 'Secret Access Key'].filter(Boolean) as string[];

  const save = async () => {
    setSaving(true);
    setSaveResult(null);
    try {
      const response = await fetch(`${API_BASE}/settings`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ apiKey, folderId, bucketName, accessKeyId, secretAccessKey, orderPrompt, yandexModel }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || `Ошибка сохранения (${response.status})`);
      onUpdate(cloudConfigFromSettings(data.settings));
      setSaveResult({ success: true, message: 'Настройки сохранены в БД.' });
      return true;
    } catch (error) {
      setSaveResult({ success: false, message: error instanceof Error ? error.message : 'Ошибка сохранения' });
      return false;
    } finally {
      setSaving(false);
    }
  };

  const check = async (service: Service) => {
    setChecks(previous => ({ ...previous, [service]: 'running' }));
    // несохранённые правки сначала сохраняем: проверяются настройки из БД
    if ((apiKey.trim() || secretAccessKey.trim()) && !(await save())) {
      setChecks(previous => ({ ...previous, [service]: undefined }));
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/test-connection`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ service }),
      });
      const data = await response.json().catch(() => ({}));
      setChecks(previous => ({ ...previous, [service]: {
        success: Boolean(response.ok && data.success),
        message: data.message || data.error || `Ответ сервера ${response.status}`,
      } }));
    } catch (error) {
      setChecks(previous => ({ ...previous, [service]: {
        success: false, message: error instanceof Error ? error.message : 'Сервер недоступен' } }));
    }
  };

  const checkButton = (service: Service, title: string, disabled: boolean) => (
    <button type="button" onClick={() => check(service)} disabled={disabled || checks[service] === 'running'}
      className="rounded-lg bg-white/10 px-3 py-2 text-sm font-medium text-white hover:bg-white/20 disabled:bg-gray-200 disabled:text-gray-700 disabled:cursor-not-allowed flex items-center gap-2">
      {checks[service] === 'running' && <Loader2 className="w-4 h-4 animate-spin" />}
      {title}
    </button>
  );

  const card = 'bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6 space-y-4';

  return (
    <div className="space-y-6">
      <div className={card}>
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <CloudIcon className="w-5 h-5 text-cyan-300" /> Яндекс Облако
        </h3>
        <p className="text-gray-200 text-sm">
          Облако нужно только для SpeechKit и YandexGPT. GigaAM и разбор по справочнику работают локально без этих настроек.
          Переключение — на вкладке «Загрузка файлов», панель «Обработка».
        </p>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label={<span className="inline-flex items-center gap-1.5"><KeyRound className="w-4 h-4 text-gray-200" /> API-ключ сервисного аккаунта *</span>}
            hint={<>IAM → сервисный аккаунт → «Создать API-ключ» (AQVN…). Один ключ для SpeechKit и YandexGPT.</>}>
            <SecretInput value={apiKey} onChange={setApiKey} saved={config.hasApiKey} placeholder="AQVN..." />
          </Field>
          <Field label="Folder ID (каталог) *"
            hint={folderId && !folderValid ? <span className="text-amber-200">Folder ID начинается с b1g</span> : 'Раздел «Каталоги», начинается с b1g'}>
            <input type="text" value={folderId} onChange={e => setFolderId(e.target.value)}
              placeholder="b1gbre1u8o8khnnig1fn" className={INPUT} />
          </Field>
        </div>
      </div>

      <div className={card}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h4 className="font-semibold text-white flex items-center gap-2">
            <Mic className="w-4 h-4 text-violet-300" /> SpeechKit — распознавание речи
          </h4>
          <Status ready={speechkitMissing.length === 0} missing={speechkitMissing} />
        </div>
        <p className="text-gray-300 text-xs">
          Роли сервисного аккаунта: <code className="bg-black/30 px-1 rounded text-gray-100">ai.speechkit-stt.user</code>,{' '}
          <code className="bg-black/30 px-1 rounded text-gray-100">storage.uploader</code>,{' '}
          <code className="bg-black/30 px-1 rounded text-gray-100">storage.editor</code>. Аудио временно загружается в бакет
          и удаляется после распознавания.
        </p>
        <Field label={<span className="inline-flex items-center gap-1.5"><Database className="w-4 h-4 text-gray-200" /> Бакет Object Storage</span>}>
          <input type="text" value={bucketName} onChange={e => setBucketName(e.target.value)}
            placeholder="speech-file" className={INPUT} />
        </Field>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Access Key ID">
            <input type="text" value={accessKeyId} onChange={e => setAccessKeyId(e.target.value)}
              placeholder="YCAJE..." className={INPUT} />
          </Field>
          <Field label="Secret Access Key">
            <SecretInput value={secretAccessKey} onChange={setSecretAccessKey}
              saved={config.hasSecretAccessKey} placeholder="YCONF..." />
          </Field>
        </div>
        <p className="text-gray-300 text-xs">IAM → сервисный аккаунт → «Создать статический ключ доступа».</p>
        {checkButton('speechkit', 'Проверить SpeechKit (загрузка в бакет)', speechkitMissing.length > 0)}
        <CheckResult check={checks.speechkit} />
      </div>

      <div className={card}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h4 className="font-semibold text-white flex items-center gap-2">
            <BrainCircuit className="w-4 h-4 text-cyan-300" /> YandexGPT — разбор заказа
          </h4>
          <Status ready={common.length === 0} missing={common} />
        </div>
        <p className="text-gray-300 text-xs">
          Нужна роль <code className="bg-black/30 px-1 rounded text-gray-100">ai.languageModels.user</code>. Бакет не нужен.
          Клиент и склейка голосовых определяются локально и при разборе через YandexGPT.
        </p>
        <Field label="Модель">
          <select value={yandexModel} onChange={e => setYandexModel(e.target.value)} className={INPUT}>
            {YANDEX_MODELS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
        </Field>
        <Field label="Дополнительные указания модели"
          hint={<>Добавляются к встроенным правилам разбора (формат JSON и проверки задаются кодом).{' '}
            <button type="button" onClick={() => setOrderPrompt(DEFAULT_ORDER_PROMPT)}
              className="underline text-cyan-200 hover:text-cyan-100">Сбросить к стандартному</button></>}>
          <textarea value={orderPrompt} onChange={e => setOrderPrompt(e.target.value)} rows={8}
            className={`${INPUT} font-mono text-xs leading-relaxed`} />
        </Field>
        {checkButton('yandexgpt', 'Проверить YandexGPT (короткий запрос)', common.length > 0)}
        <CheckResult check={checks.yandexgpt} />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button onClick={save} disabled={saving}
          className="rounded-xl bg-cyan-300 px-5 py-2.5 font-semibold text-slate-950 hover:bg-cyan-200 disabled:bg-gray-200 disabled:text-gray-700 flex items-center gap-2">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Сохранить в БД
        </button>
        {saveResult && (
          <span className={`text-sm ${saveResult.success ? 'text-emerald-300' : 'text-amber-200'}`}>{saveResult.message}</span>
        )}
      </div>
    </div>
  );
};

export default YandexCloudSettings;
