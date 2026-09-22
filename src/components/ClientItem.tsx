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
  const [expanded, setExpanded] = useState(false);

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

  const handleDeleteVariant = async (variantId: number) => {
    if (!confirm('Удалить этот вариант?')) return;

    try {
      const response = await fetch(`${BACKEND_URL}/employees/${employeeId}/dictionary/variant/${variantId}`, {
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
              <p className="text-white font-medium break-words">{client.name}</p>
            </div>
            <div className="flex flex-wrap gap-3 mt-1 text-xs text-gray-400 ml-4">
              {client.code && <span>Код: {client.code}</span>}
              {client.business_region && <span>Регион: {client.business_region}</span>}
              {client.main_manager && <span>Менеджер: {client.main_manager}</span>}
              {client.public_name && client.public_name !== client.name && (
                <span>Публ.: {client.public_name}</span>
              )}
            </div>
            
            {/* Варианты произношения (краткий вид) */}
            {client.variants && client.variants.length > 0 && !expanded && (
              <div className="mt-2 flex flex-wrap gap-1 ml-4">
                {client.variants.slice(0, 3).map((v) => (
                  <span 
                    key={v.id}
                    className="text-xs bg-green-500/20 text-green-300 px-2 py-0.5 rounded-full"
                  >
                    {v.variant}
                  </span>
                ))}
                {client.variants.length > 3 && (
                  <span className="text-xs text-gray-500">
                    +{client.variants.length - 3} ещё
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
            className="flex-shrink-0 px-2 py-1 rounded text-xs bg-green-500/20 text-green-300 hover:bg-green-500/30 transition-colors"
            title="Добавить вариант произношения"
          >
            <i className={`fas fa-${showAddVariant ? 'times' : 'plus'}`}></i>
          </button>
        </div>
      </div>

      {/* Развернутый вид с редактированием */}
      {expanded && (
        <div className="px-3 pb-3 border-t border-white/10">
          <div className="mt-3">
            <p className="text-xs text-gray-400 mb-2">Варианты произношения:</p>
            
            {client.variants && client.variants.length > 0 ? (
              <div className="space-y-1 mb-3">
                {client.variants.map((v) => (
                  <div 
                    key={v.id}
                    className="flex items-center justify-between bg-white/5 rounded px-2 py-1"
                  >
                    <span className="text-sm text-green-300">{v.variant}</span>
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
      )}
    </div>
  );
}
