import { useState } from 'react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000';

interface ClientItemData {
  id: string;
  name: string;
  code?: string;
  business_region?: string;
  main_manager?: string;
  public_name?: string;
  variants?: Array<{ id: number; variant: string; confidence: number }>;
}

interface Props {
  client: ClientItemData;
  employeeId: string;
  onVariantAdded: () => void;
}

export default function ClientItem({ client, employeeId, onVariantAdded }: Props) {
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
      const response = await fetch(`${BACKEND_URL}/employees/${employeeId}/dictionary/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          original: client.name,
          variant: newVariant.trim(),
          category: 'client'
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
          <p className="text-white font-medium break-words">{client.name}</p>
          <div className="flex flex-wrap gap-3 mt-1 text-xs text-gray-400">
            {client.code && <span>Код: {client.code}</span>}
            {client.business_region && <span>Регион: {client.business_region}</span>}
            {client.main_manager && <span>Менеджер: {client.main_manager}</span>}
            {client.public_name && client.public_name !== client.name && (
              <span>Публ.: {client.public_name}</span>
            )}
          </div>
          
          {/* Варианты произношения */}
          {client.variants && client.variants.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {client.variants.map((v) => (
                <span 
                  key={v.id}
                  className="text-xs bg-green-500/20 text-green-300 px-2 py-0.5 rounded-full"
                >
                  {v.variant}
                </span>
              ))}
            </div>
          )}
        </div>
        
        <button
          onClick={() => setShowAddVariant(!showAddVariant)}
          className="flex-shrink-0 px-2 py-1 rounded text-xs bg-green-500/20 text-green-300 hover:bg-green-500/30 transition-colors"
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
              placeholder="Например: ромашка"
              disabled={adding}
              className="flex-1 bg-white/5 border border-white/10 rounded px-2 py-1 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-400/50"
            />
            <button
              onClick={handleAddVariant}
              disabled={adding || !newVariant.trim()}
              className="px-3 py-1 rounded bg-green-500/20 text-green-300 text-sm hover:bg-green-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {adding ? <i className="fas fa-spinner fa-spin"></i> : <i className="fas fa-check"></i>}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Добавьте варианты как менеджер может назвать этого клиента
          </p>
        </div>
      )}
    </div>
  );
}
