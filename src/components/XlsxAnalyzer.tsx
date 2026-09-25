import { useState, useRef } from 'react';

// URL бэкенда
import { API } from '../api';

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

    console.log('\n' + '='.repeat(70));
    console.log('📊 [FRONTEND] Начало анализа XLSX файла');
    console.log('='.repeat(70));
    console.log(`📁 [FRONTEND] Выбран файл: ${file.name}`);
    console.log(`📏 [FRONTEND] Размер: ${(file.size / 1024 / 1024).toFixed(2)} МБ`);
    console.log(`🔗 [FRONTEND] URL бэкенда: API.analyzeXlsx`);

    setIsAnalyzing(true);
    setError(null);
    setResult(null);

    try {
      console.log('📤 [FRONTEND] Формируем FormData...');
      const formData = new FormData();
      formData.append('file', file);
      console.log('✅ [FRONTEND] FormData сформирован');

      console.log('🚀 [FRONTEND] Отправляем запрос на бэкенд...');
      const startTime = Date.now();
      
      const response = await fetch(API.analyzeXlsx, {
        method: 'POST',
        body: formData,
      });

      const elapsed = Date.now() - startTime;
      console.log(`⏱️  [FRONTEND] Запрос выполнен за ${elapsed}мс`);
      console.log(`📥 [FRONTEND] Статус ответа: ${response.status} ${response.statusText}`);

      if (!response.ok) {
        console.error(`❌ [FRONTEND] Ошибка HTTP: ${response.status}`);
        const errorData = await response.json().catch(() => ({ error: 'Ошибка сервера' }));
        console.error(`❌ [FRONTEND] Детали ошибки:`, errorData);
        throw new Error(errorData.error || `Ошибка сервера: ${response.status}`);
      }

      console.log('📥 [FRONTEND] Парсим JSON ответ...');
      const data = await response.json();
      console.log('✅ [FRONTEND] JSON успешно распарсен');
      console.log('📊 [FRONTEND] Сырой ответ:', JSON.stringify(data, null, 2));
      console.log(`📊 [FRONTEND] Получено данных:`, {
        file: data.file,
        file_size_mb: data.file_size_mb,
        sheets_count: data.sheets?.length || 0,
      });

      if (data.sheets && data.sheets.length > 0) {
        data.sheets.forEach((sheet: SheetInfo, idx: number) => {
          console.log(`   📄 Лист ${idx + 1}: ${sheet.name} (${sheet.max_row} строк × ${sheet.max_column} колонок)`);
        });
      }

      console.log('💾 [FRONTEND] Сохраняем результат в state...');
      
      // Валидация данных перед сохранением
      if (!data.sheets || !Array.isArray(data.sheets)) {
        console.warn('⚠️  [FRONTEND] Данные не содержат массив sheets, создаём пустой');
        data.sheets = [];
      }
      
      setResult(data);
      console.log('✅ [FRONTEND] Результат сохранён');
      console.log('='.repeat(70) + '\n');
      
    } catch (err) {
      console.error('\n❌ [FRONTEND] ОШИБКА ПРИ АНАЛИЗЕ:');
      console.error(err);
      console.log('='.repeat(70) + '\n');
      
      const errorMessage = err instanceof Error ? err.message : 'Неизвестная ошибка';
      setError(errorMessage);
    } finally {
      console.log('🏁 [FRONTEND] Завершаем обработку файла');
      setIsAnalyzing(false);
    }
  };

  const handleCopy = () => {
    if (!result) return;
    const text = formatResultForCopy(result);
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatResultForCopy = (data: AnalysisResult): string => {
    let text = `Файл: ${data.file || 'неизвестно'}\n`;
    text += `Размер: ${data.file_size_mb || 0} МБ\n\n`;

    if (!data.sheets || data.sheets.length === 0) {
      text += 'Листы не найдены\n';
      return text;
    }

    for (const sheet of data.sheets) {
      text += `=== ЛИСТ: ${sheet.name || 'без имени'} ===\n`;
      text += `Строк: ${sheet.max_row || 0} | Колонок: ${sheet.max_column || 0}\n\n`;

      text += `КОЛОНКИ:\n`;
      if (sheet.columns && sheet.columns.length > 0) {
        for (const col of sheet.columns) {
          text += `  ${col.letter || '?'}: ${col.header || '(без заголовка)'} [${col.type || 'unknown'}] (${col.non_empty_count || 0} заполнено)\n`;
          if (col.sample_values && col.sample_values.length > 0) {
            text += `    Примеры: ${col.sample_values.slice(0, 3).join(', ')}\n`;
          }
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
              {copied ? 'Скопировано' : 'Копировать'}
            </button>
          </div>

          {/* Информация о файле */}
          <div className="bg-black/20 rounded-xl p-4">
            <p className="text-gray-400 text-sm">
              <strong className="text-white">Файл:</strong> {result.file || 'неизвестно'}
            </p>
            <p className="text-gray-400 text-sm">
              <strong className="text-white">Размер:</strong> {result.file_size_mb || 0} МБ
            </p>
            <p className="text-gray-400 text-sm">
              <strong className="text-white">Листов:</strong> {result.sheets?.length || 0}
            </p>
          </div>

          {/* Листы */}
          {result.sheets && result.sheets.length > 0 ? (
            result.sheets.map((sheet, sheetIdx) => (
              <div key={sheetIdx} className="bg-black/20 rounded-xl p-4">
                <h5 className="text-white font-medium mb-3 flex items-center gap-2">
                  <i className="fas fa-table text-blue-400"></i>
                  Лист: {sheet.name || 'без имени'}
                  <span className="text-gray-400 text-xs font-normal">
                    ({sheet.max_row || 0} строк × {sheet.max_column || 0} колонок)
                  </span>
                </h5>

                {/* Колонки */}
                <div className="space-y-2 mb-4">
                  {sheet.columns && sheet.columns.length > 0 ? (
                    sheet.columns.map((col, colIdx) => (
                      <div key={colIdx} className="bg-white/5 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-white text-sm font-medium">
                            {col.letter || '?'}: {col.header || '(без заголовка)'}
                          </span>
                          <span className="text-xs text-gray-400">
                            {col.type || 'unknown'} • {col.non_empty_count || 0} заполнено
                          </span>
                        </div>

                        {/* Примеры значений */}
                        {col.sample_values && col.sample_values.length > 0 && (
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
                    ))
                  ) : (
                    <p className="text-gray-500 text-sm">Колонки не найдены</p>
                  )}
                </div>

                {/* Примеры строк */}
                {sheet.sample_rows && sheet.sample_rows.length > 0 && (
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
            ))
          ) : (
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4">
              <p className="text-yellow-300 text-sm">
                <i className="fas fa-exclamation-triangle mr-2"></i>
                В файле не найдено листов с данными
              </p>
            </div>
          )}

          {/* Подсказка */}
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
            <p className="text-blue-300 text-sm">
              <i className="fas fa-info-circle mr-2"></i>
              Для импорта данных перейдите на вкладку <strong>"Филиалы"</strong>, выберите филиал и используйте вкладку <strong>"Импорт"</strong>.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
