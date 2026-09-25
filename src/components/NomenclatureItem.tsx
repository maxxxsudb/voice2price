import { useState } from 'react';

import { API } from '../api';

interface NomenclatureItemData {
  id: string;
  name: string;
  article?: string;
  code?: string;
  weight?: string;
  weight_unit?: string;
  weight_denominator?: number;
  weight_numerator?: number;
  storage_unit?: string;
  max_quantity?: number | null;  // реалистичный максимум в заказе
  variants?: Array<{ id: number; variant: string; confidence: number }>;
}

interface Props {
  item: NomenclatureItemData;
  employeeId: string;
  onVariantAdded: () => void;
}

export default function NomenclatureItem({ item, employeeId, onVariantAdded }: Props) {
  const [showAddVariant, setShowAddVariant] = useState(false);
  const [newVariant, setNewVariant] = useState('');
  const [adding, setAdding] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [limitStatus, setLimitStatus] = useState('');

  // Пустое поле — действует лимит филиала из «Настроек разбора»
  const saveLimit = async (raw: string) => {
    const value = raw.trim() === '' ? null : Number(raw.replace(',', '.'));
    if (value !== null && !(value > 0)) {
      setLimitStatus('Введите положительное число или оставьте пустым');
      return;
    }
    if (value === (item.max_quantity ?? null)) return;
    setLimitStatus('Сохраняю…');
    try {
      const response = await fetch(API.employeeNomenclatureLimit(employeeId, item.id), {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_quantity: value }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Не удалось сохранить');
      setLimitStatus('Сохранено');
      onVariantAdded();
    } catch (err) {
      setLimitStatus(err instanceof Error ? err.message : 'Ошибка');
    }
  };

  const handleAddVariant = async () => {
    if (!newVariant.trim()) {
      alert('Введите вариант произношения');
      return;
    }

    setAdding(true);
    try {
      const response = await fetch(API.employeeDictionaryAdd(employeeId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          original: item.name,
          variant: newVariant.trim(),
          category: 'nomenclature'
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to add variant');
      }

      setNewVariant('');
      setShowAddVariant(false);
      onVariantAdded();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to add variant');
    } finally {
      setAdding(false);
    }
  };

  const handleDeleteVariant = async (variantId: number) => {
    if (!confirm('Удалить этот вариант?')) return;

    try {
      const response = await fetch(API.employeeDictionaryVariant(employeeId, variantId), {
        method: 'DELETE',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to delete variant');
      }

      onVariantAdded();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete variant');
    }
  };

  return (
    <div className="bg-white/5 rounded-lg border border-white/10 hover:border-white/20 transition-colors">
      {/* Основная информация */}
      <div 
        className="p-3 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <i className={`fas fa-chevron-${expanded ? 'down' : 'right'} text-gray-500 text-xs`}></i>
              <p className="text-white font-medium break-words">{item.name}</p>
            </div>
            <div className="flex flex-wrap gap-3 mt-1 text-xs text-gray-400 ml-4">
              {item.article && <span>Артикул: {item.article}</span>}
              {item.code && <span>Код: {item.code}</span>}
              {item.weight && <span>Вес: {item.weight}</span>}
              {item.weight_unit && <span>Ед.: {item.weight_unit}</span>}
              {item.max_quantity != null && <span>Макс. в заказе: {item.max_quantity} {item.storage_unit ?? ''}</span>}
            </div>
            
            {/* Варианты произношения (краткий вид) */}
            {item.variants && item.variants.length > 0 && !expanded && (
              <div className="mt-2 flex flex-wrap gap-1 ml-4">
                {item.variants.slice(0, 3).map((v) => (
                  <span 
                    key={v.id}
                    className="text-xs bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded-full"
                  >
                    {v.variant}
                  </span>
                ))}
                {item.variants.length > 3 && (
                  <span className="text-xs text-gray-500">
                    +{item.variants.length - 3} ещё
                  </span>
                )}
              </div>
            )}
          </div>
          
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowAddVariant(!showAddVariant);
            }}
            className="flex-shrink-0 px-2 py-1 rounded text-xs bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 transition-colors"
            title="Добавить вариант произношения"
          >
            <i className={`fas fa-${showAddVariant ? 'times' : 'plus'}`}></i>
          </button>
        </div>
      </div>

      {/* Развернутый вид с редактированием */}
      {expanded && (
        <div className="px-3 pb-3 border-t border-white/10">
          <label className="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-300">
            Реалистичный максимум в заказе:
            <input
              type="text" inputMode="decimal"
              defaultValue={item.max_quantity ?? ''}
              key={String(item.max_quantity ?? '')}
              placeholder="лимит филиала"
              onBlur={(e) => saveLimit(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && saveLimit((e.target as HTMLInputElement).value)}
              className="w-28 bg-white/5 border border-white/10 rounded px-2 py-1 text-sm text-white placeholder-gray-500"
            />
            {item.storage_unit ?? ''}
            {limitStatus && <span role="status" className="text-gray-300">{limitStatus}</span>}
          </label>
          <div className="mt-3">
            <p className="text-xs text-gray-400 mb-2">Варианты произношения:</p>
            
            {item.variants && item.variants.length > 0 ? (
              <div className="space-y-1 mb-3">
                {item.variants.map((v) => (
                  <div 
                    key={v.id}
                    className="flex items-center justify-between bg-white/5 rounded px-2 py-1"
                  >
                    <span className="text-sm text-purple-300">{v.variant}</span>
                    <button
                      onClick={() => handleDeleteVariant(v.id)}
                      className="text-red-400 hover:text-red-300 transition-colors text-xs"
                      title="Удалить вариант"
                    >
                      <i className="fas fa-trash"></i>
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-500 mb-3">Варианты не добавлены</p>
            )}
          </div>

          {/* Форма добавления варианта */}
          {showAddVariant && (
            <div className="pt-3 border-t border-white/10">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newVariant}
                  onChange={(e) => setNewVariant(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddVariant()}
                  placeholder="Например: молоко домик"
                  disabled={adding}
                  className="flex-1 bg-white/5 border border-white/10 rounded px-2 py-1 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-purple-400/50"
                />
                <button
                  onClick={handleAddVariant}
                  disabled={adding || !newVariant.trim()}
                  className="px-3 py-1 rounded bg-purple-500/20 text-purple-300 text-sm hover:bg-purple-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {adding ? <i className="fas fa-spinner fa-spin"></i> : <i className="fas fa-check"></i>}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Добавьте варианты как менеджер может назвать этот товар
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
