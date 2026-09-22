import { useState } from 'react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000';

interface UnitItemData {
  id: string;
  name: string;
  abbreviation?: string;
  category?: string;
  variants?: Array<{ id: number; variant: string; confidence: number }>;
}

interface Props {
  unit: UnitItemData;
  employeeId: string;
  onVariantAdded: () => void;
}

export default function UnitItem({ unit, employeeId, onVariantAdded }: Props) {
  const [showAddVariant, setShowAddVariant] = useState(false);
  const [newVariant, setNewVariant] = useState('');
  const [adding, setAdding] = useState(false);

  const handleAddVariant = async () => {
    if (!newVariant.trim()) {
      alert('Введите вариант произношения');
      return;
    }

    setAdding(true);
    try {
      const response = await fetch(`${BACKEND_URL}/employees/${employeeId}/units/${unit.id}/variants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          variant: newVariant.trim()
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

  return (
    <div className="bg-white/5 rounded-lg p-3 border border-white/10 hover:border-white/20 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-white font-medium">{unit.name}</p>
            {unit.abbreviation && (
              <span className="text-xs bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded">
                {unit.abbreviation}
              </span>
            )}
          </div>
          {unit.category && (
            <p className="text-xs text-gray-400 mt-1">Категория: {unit.category}</p>
          )}
          
          {/* Варианты произношения */}
          {unit.variants && unit.variants.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {unit.variants.map((v) => (
                <span 
                  key={v.id}
                  className="text-xs bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded-full"
                >
                  {v.variant}
                </span>
              ))}
            </div>
          )}
        </div>
        
        <button
          onClick={() => setShowAddVariant(!showAddVariant)}
          className="flex-shrink-0 px-2 py-1 rounded text-xs bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 transition-colors"
          title="Добавить вариант произношения"
        >
          <i className={`fas fa-${showAddVariant ? 'times' : 'plus'}`}></i>
        </button>
      </div>

      {/* Форма добавления варианта */}
      {showAddVariant && (
        <div className="mt-3 pt-3 border-t border-white/10">
          <div className="flex gap-2">
            <input
              type="text"
              value={newVariant}
              onChange={(e) => setNewVariant(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddVariant()}
              placeholder="Например: полкило, 300 грамм"
              disabled={adding}
              className="flex-1 bg-white/5 border border-white/10 rounded px-2 py-1 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400/50"
            />
            <button
              onClick={handleAddVariant}
              disabled={adding || !newVariant.trim()}
              className="px-3 py-1 rounded bg-cyan-500/20 text-cyan-300 text-sm hover:bg-cyan-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {adding ? <i className="fas fa-spinner fa-spin"></i> : <i className="fas fa-check"></i>}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Добавьте варианты как менеджер может назвать эту единицу измерения
          </p>
        </div>
      )}
    </div>
  );
}
