import { useState } from 'react';
import type { RecognitionResult, NomenclatureMatch } from '../types';

interface Props {
  terms: string[];
  onAddTerm: (term: string) => void;
  onRemoveTerm: (term: string) => void;
  results: RecognitionResult[];
}

export default function NomenclatureSearch({ terms, onAddTerm, onRemoveTerm, results }: Props) {
  const [input, setInput] = useState('');
  const [bulkInput, setBulkInput] = useState('');
  const [showBulk, setShowBulk] = useState(false);

  const handleAdd = () => {
    if (input.trim()) {
      onAddTerm(input.trim());
      setInput('');
    }
  };

  const handleBulkAdd = () => {
    const newTerms = bulkInput
      .split(/[\n,;]+/)
      .map(t => t.trim())
      .filter(t => t.length > 0);
    newTerms.forEach(t => onAddTerm(t));
    setBulkInput('');
    setShowBulk(false);
  };

  const findMatches = (): NomenclatureMatch[] => {
    const matches: NomenclatureMatch[] = [];
    for (const result of results) {
      if (result.status !== 'success' || !result.text) continue;
      const textLower = result.text.toLowerCase();
      for (const term of terms) {
        const termLower = term.toLowerCase();
        let start = 0;
        while (true) {
          const pos = textLower.indexOf(termLower, start);
          if (pos === -1) break;
          const ctxStart = Math.max(0, pos - 40);
          const ctxEnd = Math.min(result.text.length, pos + term.length + 40);
          matches.push({
            term,
            fileName: result.fileName,
            context: result.text.substring(ctxStart, ctxEnd),
            position: pos,
          });
          start = pos + 1;
        }
      }
    }
    return matches;
  };

  const matches = findMatches();

  const presets = [
    'артикул', 'серийный номер', 'модель', 'партия',
    'дата производства', 'срок годности', 'ГОСТ', 'ТУ',
    'количество', 'цена', 'наименование', 'поставщик'
  ];

  return (
    <div className="space-y-6">
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <i className="fas fa-tags text-purple-400"></i>
          Термины номенклатуры
        </h3>

        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            placeholder="Введите термин..."
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-400/50 focus:ring-1 focus:ring-purple-400/50 transition-all"
          />
          <button
            onClick={handleAdd}
            className="px-5 py-3 rounded-xl bg-purple-500/20 text-purple-300 font-medium hover:bg-purple-500/30 transition-colors"
          >
            <i className="fas fa-plus mr-1"></i> Добавить
          </button>
        </div>

        <button
          onClick={() => setShowBulk(!showBulk)}
          className="text-sm text-gray-400 hover:text-white transition-colors flex items-center gap-1"
        >
          <i className={`fas fa-chevron-${showBulk ? 'up' : 'down'} text-xs`}></i>
          Массовый ввод
        </button>

        {showBulk && (
          <div className="mt-3">
            <textarea
              value={bulkInput}
              onChange={(e) => setBulkInput(e.target.value)}
              placeholder="Введите термины через запятую, точку с запятой или с новой строки..."
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-purple-400/50 resize-none"
            />
            <button
              onClick={handleBulkAdd}
              className="mt-2 px-4 py-2 rounded-lg bg-purple-500/20 text-purple-300 text-sm hover:bg-purple-500/30 transition-colors"
            >
              Добавить все
            </button>
          </div>
        )}

        {terms.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {terms.map((term) => (
              <span
                key={term}
                className="inline-flex items-center gap-2 bg-purple-500/20 text-purple-300 text-sm px-3 py-1.5 rounded-full"
              >
                {term}
                <button onClick={() => onRemoveTerm(term)} className="hover:text-white transition-colors">
                  <i className="fas fa-xmark text-xs"></i>
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="mt-4 pt-4 border-t border-white/10">
          <p className="text-gray-400 text-xs mb-2">Быстрые примеры:</p>
          <div className="flex flex-wrap gap-1.5">
            {presets.map((preset) => (
              <button
                key={preset}
                onClick={() => onAddTerm(preset)}
                disabled={terms.includes(preset)}
                className="text-xs px-2.5 py-1 rounded-full bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                + {preset}
              </button>
            ))}
          </div>
        </div>
      </div>

      {results.length > 0 && terms.length > 0 && (
        <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <i className="fas fa-search text-green-400"></i>
            Результаты поиска
            <span className="text-sm font-normal text-gray-400">({matches.length} совпадений)</span>
          </h3>

          {matches.length === 0 ? (
            <p className="text-gray-400 text-sm">Совпадений не найдено</p>
          ) : (
            <div className="space-y-3">
              {matches.map((match, idx) => (
                <div key={idx} className="bg-black/20 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="bg-green-500/20 text-green-300 text-xs px-2 py-0.5 rounded-full">{match.term}</span>
                    <span className="text-gray-400 text-xs">
                      <i className="fas fa-file mr-1"></i>{match.fileName}
                    </span>
                  </div>
                  <p className="text-gray-200 text-sm">...{match.context}...</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {results.length === 0 && (
        <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-12 text-center">
          <i className="fas fa-magnifying-glass text-4xl text-gray-600 mb-4"></i>
          <p className="text-gray-400">Сначала выполните распознавание файлов</p>
        </div>
      )}
    </div>
  );
}
