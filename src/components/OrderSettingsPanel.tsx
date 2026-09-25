import { useEffect, useState } from 'react';
import { API } from '../api';
import type { OrderSettings } from '../types';

interface Props {
  employeeId: string;
}

const SWITCHES: { key: keyof OrderSettings; title: string; hint: string }[] = [
  { key: 'plausibility', title: 'Проверять реалистичность количества',
    hint: 'Только там, где задан максимум: у позиции номенклатуры («Реалистичный максимум в заказе») или общий лимит ниже. Без максимума количество не проверяется.' },
  { key: 'grams_over_limit', title: 'Понимать граммы',
    hint: '«Сосиски пятьсот» при максимуме 5 кг и без сказанной единицы — это 500 г: количество станет 0.5 кг с пометкой, без отправки на проверку.' },
  { key: 'size_in_name', title: 'Число из названия — это фасовка, а не количество',
    hint: '«Зельц двести пятьдесят» при товаре «Зельц 250 гр»: число выбирает товар, а количество нужно уточнить.' },
  { key: 'corrections', title: 'Понимать поправки в речи',
    hint: '«Два кило, точнее три», «пять, нет, семь» — меняется количество предыдущей позиции, а не добавляется новая строка.' },
  { key: 'detect_client', title: 'Определять клиента',
    hint: 'Клиент ищется в начале сообщения по справочнику клиентов филиала и вариантам произношения.' },
  { key: 'merge_messages', title: 'Склеивать подряд идущие голосовые одного клиента',
    hint: 'Продолжение заказа в следующем сообщении попадает в тот же заказ. Причина склейки видна в результате.' },
];

// Пустое поле лимита — лимит филиала не задан, действует только максимум позиции
const LIMITS: { key: 'max_kg' | 'max_pcs' | 'max_packs'; title: string; unit: string }[] = [
  { key: 'max_kg', title: 'Общий максимум для весовых позиций', unit: 'кг' },
  { key: 'max_pcs', title: 'Общий максимум для штучных позиций', unit: 'шт' },
  { key: 'max_packs', title: 'Общий максимум для упаковок', unit: 'уп' },
];

export default function OrderSettingsPanel({ employeeId }: Props) {
  const [settings, setSettings] = useState<OrderSettings | null>(null);
  const [status, setStatus] = useState('');

  useEffect(() => {
    let cancelled = false;
    fetch(API.employeeOrderSettings(employeeId))
      .then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Не удалось загрузить опции');
        if (!cancelled) setSettings(data.settings);
      })
      .catch(err => { if (!cancelled) setStatus(err instanceof Error ? err.message : 'Ошибка'); });
    return () => { cancelled = true; };
  }, [employeeId]);

  const save = async (patch: Partial<OrderSettings>) => {
    setStatus('Сохраняю…');
    try {
      const response = await fetch(API.employeeOrderSettings(employeeId), {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Не удалось сохранить');
      setSettings(data.settings);
      setStatus('Сохранено');
    } catch (err) {
      setStatus(err instanceof Error ? err.message : 'Ошибка сохранения');
    }
  };

  if (!settings) return <p className="text-gray-100">{status || 'Загрузка опций…'}</p>;
  return (
    <div className="space-y-4">
      <p className="text-gray-300 text-sm">
        Опции разбора голосовых заказов этого филиала. Каждую проверку можно отключить.
      </p>
      {SWITCHES.map(({ key, title, hint }) => (
        <label key={key} className="flex items-start gap-3 rounded-xl bg-gray-900 p-3 cursor-pointer">
          <input type="checkbox" className="mt-1 w-4 h-4 accent-yellow-400" checked={Boolean(settings[key])}
            onChange={e => save({ [key]: e.target.checked })} />
          <span>
            <span className="block text-gray-100 text-sm font-medium">{title}</span>
            <span className="block text-gray-300 text-xs mt-0.5">{hint}</span>
          </span>
        </label>
      ))}
      <div className="grid gap-3 sm:grid-cols-2">
        {LIMITS.map(({ key, title, unit }) => (
          <label key={key} className="rounded-xl bg-gray-900 p-3 text-sm text-gray-100">
            <span className="block">{title}</span>
            <span className="block text-gray-300 text-xs">Для позиций без своего максимума. Пусто — не проверять.</span>
            <span className="mt-1 flex items-center gap-2">
              <input type="text" inputMode="decimal" placeholder="не задан"
                defaultValue={settings[key] ?? ''} key={`${key}-${settings[key]}`}
                className="w-28 rounded-lg border border-white/20 bg-black/40 px-2 py-1 text-gray-100 placeholder-gray-500"
                onBlur={e => {
                  const raw = e.target.value.trim().replace(',', '.');
                  const value = raw === '' ? null : Number(raw);
                  if (value !== null && !(value > 0)) { setStatus('Введите положительное число или оставьте пустым'); return; }
                  if (value !== settings[key]) save({ [key]: value });
                }} />
              {unit}
            </span>
          </label>
        ))}
        <label className="rounded-xl bg-gray-900 p-3 text-sm text-gray-100">
          <span className="block">Склеивать, если между сообщениями не больше</span>
          <span className="mt-1 flex items-center gap-2">
            <input type="number" min="1" step="any" defaultValue={settings.merge_window_min}
              key={`merge-${settings.merge_window_min}`}
              className="w-28 rounded-lg border border-white/20 bg-black/40 px-2 py-1 text-gray-100"
              onBlur={e => {
                const value = Number(e.target.value);
                if (value > 0 && value !== settings.merge_window_min) save({ merge_window_min: value });
              }} />
            мин
          </span>
        </label>
      </div>
      {status && <p role="status" className="text-gray-300 text-sm">{status}</p>}
    </div>
  );
}
