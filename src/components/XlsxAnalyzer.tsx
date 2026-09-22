import { useState, useRef } from 'react';

// URL бэкенда
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000';

interface ColumnInfo {
  letter: string;
  header: string | null;
  type: string;
  non_empty_count: number;
  sample_values: any[];
  stats?: {
    min: number;
    max: number;
    avg: number;
  };
}

interface SheetInfo {
  name: string;
  max_row: number;
  max_column: number;
  columns: ColumnInfo[];
  sample_rows: Record<string, any>[];
}

interface AnalysisResult {
  file: string;
  file_size_mb: number;
  sheets: SheetInfo[];
}

export default function XlsxAnalyzer() {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsAnalyzing(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${BACKEND_URL}/analyze-xlsx`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Ошибка сервера' }));
        throw new Error(errorData.error || `Ошибка: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleCopy = () => {
    if (!result) return;

    // Формируем текст для копирования
    const text = formatResultForCopy(result);
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatResultForCopy = (data: AnalysisResult): string => {
    let text = `Файл: ${data.file}\n`;
    text += `Размер: ${data.file_size_mb} МБ\n\n`;

    for (const sheet of data.sheets) {
      text += `=== ЛИСТ: ${sheet.name} ===\n`;
      text += `Строк: ${sheet.max_row} | Колонок: ${sheet.max_column}\n\n`;

      text += `КОЛОНКИ:\n`;
      for (const col of sheet.columns) {
        text += `  ${col.letter}: ${col.header || '(без заголовка)'} [${col.type}] (${col.non_empty_count} заполнено)\n`;
        if (col.sample_values.length > 0) {
          text += `    Примеры: ${col.sample_values.slice(0, 3).join(', ')}\n`;
        }
        if (col.stats) {
          text += `    Min: ${col.stats.min}, Max: ${col.stats.max}, Avg: ${col.stats.avg.toFixed(2)}\n`;
        }
      }

      text += `\nПРИМЕРЫ СТРОК:\n`;
      for (let i = 0; i < sheet.sample_rows.length; i++) {
        text += `  Строка ${i + 1}:\n`;
        for (const [key, value] of Object.entries(sheet.sample_rows[i])) {
          text += `    ${key}: ${value}\n`;
        }
      }
      text += `\n`;
    }

    return text;
  };

  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
      <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
        <i className="fas fa-file-excel text-green-400"></i>
        Анализ XLSX файла
      </h3>

      <p className="text-gray-400 text-sm mb-4">
        Загрузите XLSX файл (номенклатура или клиенты) для анализа структуры данных.
        После анализа скопируйте результат для генерации импортера.
      </p>

      <input
        ref={inputRef}
        type="file"
        accept=".xlsx"
        onChange={handleFileChange}
        className="hidden"
      />

      <button
        onClick={() => inputRef.current?.click()}
        disabled={isAnalyzing}
        className="w-full py-3 rounded-xl bg-green-500/20 text-green-300 font-medium hover:bg-green-500/30 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
      >
        {isAnalyzing ? (
          <>
            <i className="fas fa-spinner fa-spin"></i>
            Анализ...
          </>
        ) : (
          <>
            <i className="fas fa-file-excel"></i>
            Выбрать XLSX файл
          </>
        )}
      </button>

      {/* Ошибка */}
      {error && (
        <div className="mt-4 bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <p className="text-red-300 text-sm">
            <i className="fas fa-exclamation-circle mr-2"></i>
            {error}
          </p>
        </div>
      )}

      {/* Результат анализа */}
      {result && (
        <div className="mt-6 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-white font-semibold flex items-center gap-2">
              <i className="fas fa-check-circle text-green-400"></i>
              Результат анализа
            </h4>
            <button
              onClick={handleCopy}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                copied
                  ? 'bg-green-500/20 text-green-300'
                  : 'bg-white/5 text-gray-300 hover:bg-white/10'
              }`}
            >
              <i className={`fas ${copied ? 'fa-check' : 'fa-copy'}`}></i>
              {copied ? 'Скопировано' : 'Копировать для импортера'}
            </button>
          </div>

          {/* Информация о файле */}
          <div className="bg-black/20 rounded-xl p-4">
            <p className="text-gray-400 text-sm">
              <strong className="text-white">Файл:</strong> {result.file}
            </p>
            <p className="text-gray-400 text-sm">
              <strong className="text-white">Размер:</strong> {result.file_size_mb} МБ
            </p>
            <p className="text-gray-400 text-sm">
              <strong className="text-white">Листов:</strong> {result.sheets.length}
            </p>
          </div>

          {/* Листы */}
          {result.sheets.map((sheet, sheetIdx) => (
            <div key={sheetIdx} className="bg-black/20 rounded-xl p-4">
              <h5 className="text-white font-medium mb-3 flex items-center gap-2">
                <i className="fas fa-table text-blue-400"></i>
                Лист: {sheet.name}
                <span className="text-gray-400 text-xs font-normal">
                  ({sheet.max_row} строк × {sheet.max_column} колонок)
                </span>
              </h5>

              {/* Колонки */}
              <div className="space-y-2 mb-4">
                {sheet.columns.map((col, colIdx) => (
                  <div key={colIdx} className="bg-white/5 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-white text-sm font-medium">
                        {col.letter}: {col.header || '(без заголовка)'}
                      </span>
                      <span className="text-xs text-gray-400">
                        {col.type} • {col.non_empty_count} заполнено
                      </span>
                    </div>

                    {/* Примеры значений */}
                    {col.sample_values.length > 0 && (
                      <div className="text-xs text-gray-400 mt-1">
                        Примеры: {col.sample_values.slice(0, 3).map(v => String(v)).join(', ')}
                      </div>
                    )}

                    {/* Статистика */}
                    {col.stats && (
                      <div className="text-xs text-gray-400 mt-1">
                        Min: {col.stats.min} • Max: {col.stats.max} • Avg: {col.stats.avg.toFixed(2)}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Примеры строк */}
              {sheet.sample_rows.length > 0 && (
                <div>
                  <p className="text-gray-400 text-xs mb-2">Примеры строк:</p>
                  <div className="space-y-1">
                    {sheet.sample_rows.map((row, rowIdx) => (
                      <div key={rowIdx} className="bg-white/5 rounded p-2 text-xs">
                        {Object.entries(row).map(([key, value]) => (
                          <div key={key} className="text-gray-300">
                            <span className="text-gray-500">{key}:</span> {String(value)}
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Подсказка */}
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
            <p className="text-blue-300 text-sm">
              <i className="fas fa-lightbulb mr-2"></i>
              Скопируйте результат и передайте его для генерации импортера номенклатуры и клиентов.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
