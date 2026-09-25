import { useEffect, useState } from 'react';
import { Cpu, Cloud, BookOpen, BrainCircuit, CheckCircle, AlertTriangle, RotateCw } from 'lucide-react';
import { API } from '../api';
import type { EngineOption, EnginesInfo, OrderParser, SttEngine } from '../types';

// Что выбрать: распознавание (GigaAM / SpeechKit) и разбор заказа (справочник / YandexGPT).
// Готовность каждого варианта приходит с сервера (/api/engines).

interface Choice<T extends string> {
  id: T;
  title: string;
  subtitle: string;
  icon: JSX.Element;
}

const STT: Choice<SttEngine>[] = [
  { id: 'gigaam', title: 'GigaAM', subtitle: 'Локально · бесплатно · аудио не уходит', icon: <Cpu className="w-4 h-4" /> },
  { id: 'speechkit', title: 'SpeechKit', subtitle: 'Яндекс Облако · платно', icon: <Cloud className="w-4 h-4" /> },
];

const PARSERS: Choice<OrderParser>[] = [
  { id: 'rules', title: 'По справочнику', subtitle: 'Локально · проверки в коде', icon: <BookOpen className="w-4 h-4" /> },
  { id: 'llm', title: 'YandexGPT', subtitle: 'Яндекс Облако · платно', icon: <BrainCircuit className="w-4 h-4" /> },
];

function Segmented<T extends string>({ label, choices, value, onChange, options, disabled }: {
  label: string;
  choices: Choice<T>[];
  value: T;
  onChange: (value: T) => void;
  options?: EngineOption[];
  disabled?: boolean;
}) {
  const current = options?.find(option => option.id === value);
  return (
    <div className={disabled ? 'opacity-60' : ''}>
      <p className="text-gray-200 text-xs uppercase tracking-wide mb-2">{label}</p>
      <div className="grid grid-cols-2 gap-1 rounded-xl bg-black/30 p-1" role="radiogroup" aria-label={label}>
        {choices.map(choice => {
          const selected = choice.id === value;
          const status = options?.find(option => option.id === choice.id);
          return (
            <button
              key={choice.id}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={disabled}
              onClick={() => onChange(choice.id)}
              className={`rounded-lg px-3 py-2 text-left transition-colors disabled:cursor-not-allowed ${selected
                ? 'bg-cyan-300 text-slate-950 shadow' : 'text-gray-100 hover:bg-white/10'}`}
            >
              <span className="flex items-center gap-2 text-sm font-semibold">
                {choice.icon}
                {choice.title}
                {status && !status.ready && (
                  <AlertTriangle className={`w-3.5 h-3.5 ${selected ? 'text-amber-800' : 'text-amber-300'}`}
                    aria-label="не готово" />
                )}
              </span>
              <span className={`block text-xs mt-0.5 ${selected ? 'text-slate-800' : 'text-gray-300'}`}>
                {choice.subtitle}
              </span>
            </button>
          );
        })}
      </div>
      {current && !disabled && (
        <p className={`mt-2 text-xs flex items-start gap-1.5 ${current.ready ? 'text-emerald-300' : 'text-amber-200'}`}>
          {current.ready
            ? <><CheckCircle className="w-3.5 h-3.5 mt-px shrink-0" />{current.detail}</>
            : <><AlertTriangle className="w-3.5 h-3.5 mt-px shrink-0" />
                {current.missing.length ? `Не заполнено: ${current.missing.join(', ')}` : current.detail}</>}
        </p>
      )}
    </div>
  );
}

export function useEngines(refreshKey: unknown) {
  const [engines, setEngines] = useState<EnginesInfo | null>(null);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let cancelled = false;
    fetch(API.engines)
      .then(response => response.ok ? response.json() : null)
      .then(data => { if (!cancelled && data?.stt) setEngines(data); })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, [refreshKey, reload]);
  return { engines, refresh: () => setReload(n => n + 1) };
}

export function isReady(engines: EnginesInfo | null, kind: 'stt' | 'parser', id: string) {
  // пока сервер не ответил — не блокируем кнопку
  return engines?.[kind].options.find(option => option.id === id)?.ready ?? true;
}

interface Props {
  engines: EnginesInfo | null;
  onRefresh: () => void;
  sttEngine: SttEngine;
  onSttEngine: (value: SttEngine) => void;
  processOrder: boolean;
  onProcessOrder: (value: boolean) => void;
  parser: OrderParser;
  onParser: (value: OrderParser) => void;
  onOpenSettings: () => void;
}

export default function ProcessingPanel(props: Props) {
  const { engines } = props;
  const cloudMissing = (props.sttEngine === 'speechkit' && !isReady(engines, 'stt', 'speechkit'))
    || (props.processOrder && props.parser === 'llm' && !isReady(engines, 'parser', 'llm'));
  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-semibold">Обработка</h3>
        <button type="button" onClick={props.onRefresh}
          className="text-gray-200 hover:text-white text-xs flex items-center gap-1" title="Проверить готовность">
          <RotateCw className="w-3.5 h-3.5" /> Проверить
        </button>
      </div>
      <div className="grid gap-5 md:grid-cols-2">
        <Segmented label="Распознавание речи" choices={STT} value={props.sttEngine}
          onChange={props.onSttEngine} options={engines?.stt.options} />
        <div>
          <Segmented label="Разбор заказа" choices={PARSERS} value={props.parser}
            onChange={props.onParser} options={engines?.parser.options} disabled={!props.processOrder} />
          <label className="mt-3 flex items-center gap-2 cursor-pointer select-none">
            <input type="checkbox" checked={props.processOrder}
              onChange={event => props.onProcessOrder(event.target.checked)}
              className="w-4 h-4 accent-cyan-300" />
            <span className="text-gray-100 text-sm">
              Разобрать в заказы (голосовые одного клиента склеиваются)
            </span>
          </label>
        </div>
      </div>
      <p className="mt-4 text-gray-300 text-xs">
        Клиент определяется всегда, когда выбран филиал: по его справочнику клиентов и сокращениям из словаря.
      </p>
      {cloudMissing && (
        <button type="button" onClick={props.onOpenSettings}
          className="mt-3 text-amber-200 underline hover:text-amber-100 text-sm">
          Заполнить настройки Яндекс Облака →
        </button>
      )}
    </div>
  );
}
