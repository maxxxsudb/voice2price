import { useEffect, useState } from 'react';
import { API } from '../api';
import type { OrderSettings } from '../types';

interface Props {
  employeeId: string;
}

const SWITCHES: { key: keyof OrderSettings; title: string; hint: string }[] = [
  { key: 'plausibility', title: 'Проверять реалистичность количества',
    hint: 'Количество больше лимита уходит на проверку. Лимит позиции задаётся в номенклатуре, иначе действует лимит филиала ниже.' },
  { key: 'suggest_grams', title: 'Подсказывать граммы',
    hint: '«Сосиски пятьсот» при лимите 5 кг: подсказка «возможно, 0.5 кг». Количество само не меняется.' },
  { key: 'corrections', title: 'Понимать поправки в речи',
    hint: '«Два кило, точнее три», «пять, нет, семь» — меняется количество предыдущей позиции, а не добавляется новая строка.' },
  { key: 'detect_client', title: 'Определять клиента',
    hint: 'Клиент ищется в начале сообщения по справочнику клиентов филиала и вариантам произношения.' },
  { key: 'merge_messages', title: 'Склеивать подряд идущие голосовые одного клиента',
    hint: 'Продолжение заказа в следующем сообщении попадает в тот же заказ. Причина склейки видна в результате.' },
];

const NUMBERS: { key: keyof OrderSettings; title: string; unit: string }[] = [
  { key: 'max_kg', title: 'Лимит для товаров в кг', unit: 'кг' },
  { key: 'max_pcs', title: 'Лимит для товаров в штуках', unit: 'шт' },
  { key: 'max_packs', title: 'Лимит для упаковок', unit: 'уп' },
  { key: 'merge_window_min', title: 'Склеивать, если между сообщениями не больше', unit: 'мин' },
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
        {NUMBERS.map(({ key, title, unit }) => (
          <label key={key} className="rounded-xl bg-gray-900 p-3 text-sm text-gray-100">
            <span className="block">{title}</span>
            <span className="mt-1 flex items-center gap-2">
              <input type="number" min="0.001" step="any" defaultValue={Number(settings[key])}
                key={`${key}-${settings[key]}`}
                className="w-28 rounded-lg border border-white/20 bg-black/40 px-2 py-1 text-gray-100"
                onBlur={e => {
                  const value = Number(e.target.value);
                  if (value > 0 && value !== settings[key]) save({ [key]: value });
                }} />
              {unit}
            </span>
          </label>
        ))}
      </div>
      {status && <p role="status" className="text-gray-300 text-sm">{status}</p>}
    </div>
  );
}
