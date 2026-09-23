import type { RecognitionResult, OrderItem, TranscriptSegment } from '../types';

interface Props {
  results: RecognitionResult[];
  onClear: () => void;
}

// "12.345s" -> "0:12.3" (мм:сс.д), пусто — если таймкода нет
function fmtTime(t?: string): string {
  if (!t) return '';
  const sec = parseFloat(t);
  if (Number.isNaN(sec)) return t;
  const m = Math.floor(sec / 60);
  const s = (sec - m * 60).toFixed(1);
  return `${m}:${s.padStart(4, '0')}`;
}

function TranscriptSegments({ segments }: { segments: TranscriptSegment[] }) {
  return (
    <div className="mt-3 max-h-72 overflow-y-auto rounded-xl border border-white/10 divide-y divide-white/5">
      {segments.map((seg, i) => (
        <div key={i} className="flex items-start gap-3 px-4 py-2 bg-black/20">
          <span className="text-gray-500 text-xs font-mono whitespace-nowrap pt-0.5 min-w-[80px]">
            {fmtTime(seg.startTime)}{seg.endTime ? ` – ${fmtTime(seg.endTime)}` : ''}
          </span>
          <span className="text-gray-200 text-sm leading-relaxed">{seg.text || '—'}</span>
        </div>
      ))}
    </div>
  );
}

function OrderItemsTable({ items }: { items: OrderItem[] }) {
  return (
    <div className="mt-3 overflow-x-auto rounded-xl border border-white/10">
      <table className="w-full text-sm">
        <thead className="bg-white/10 text-gray-300">
          <tr>
            <th className="text-left px-4 py-2 font-medium">№</th>
            <th className="text-left px-4 py-2 font-medium">Наименование</th>
            <th className="text-right px-4 py-2 font-medium">Кол-во</th>
            <th className="text-left px-4 py-2 font-medium">Ед.</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i} className="border-t border-white/5">
              <td className="px-4 py-2 text-gray-500">{i + 1}</td>
              <td className="px-4 py-2 text-gray-200">{String(item.name ?? '—')}</td>
              <td className="px-4 py-2 text-right text-white font-medium">{String(item.quantity ?? 1)}</td>
              <td className="px-4 py-2 text-gray-400">{String(item.unit ?? 'шт')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function RecognitionResults({ results, onClear }: Props) {
  if (results.length === 0) {
    return (
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-12 text-center">
        <i className="fas fa-file-lines text-4xl text-gray-600 mb-4"></i>
        <p className="text-gray-400">Нет результатов распознавания</p>
        <p className="text-gray-500 text-sm mt-1">Загрузите файлы и запустите распознавание</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-white font-semibold text-lg flex items-center gap-2">
          <i className="fas fa-file-lines text-green-400"></i>
          Результаты распознавания
        </h3>
        <button
          onClick={onClear}
          className="text-sm text-red-400 hover:text-red-300 transition-colors flex items-center gap-1"
        >
          <i className="fas fa-trash"></i>
          Очистить
        </button>
      </div>

      {results.map((result, idx) => (
        <div
          key={`${result.fileId}-${idx}`}
          className={`bg-white/5 backdrop-blur-sm rounded-2xl border p-6 ${
            result.status === 'error' ? 'border-red-500/30' : 'border-white/10'
          }`}
        >
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                result.status === 'success' ? 'bg-green-500/20' : 'bg-red-500/20'
              }`}>
                <i className={`fas ${result.status === 'success' ? 'fa-check text-green-400' : 'fa-xmark text-red-400'}`}></i>
              </div>
              <div>
                <p className="text-white font-medium text-sm">{result.fileName}</p>
                {result.status === 'success' && (
                  <p className="text-gray-400 text-xs">
                    Уверенность: {(result.confidence * 100).toFixed(1)}%
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={() => { navigator.clipboard.writeText(result.text); }}
              className="text-gray-400 hover:text-white transition-colors text-sm"
              title="Копировать текст"
            >
              <i className="fas fa-copy"></i>
            </button>
          </div>

          {result.status === 'success' ? (
            <div className="bg-black/20 rounded-xl p-4">
              <p className="text-gray-500 text-[10px] uppercase tracking-wide mb-1 flex items-center gap-1">
                <i className="fas fa-microphone"></i>
                Текст распознавания (SpeechKit)
              </p>
              <p className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap">
                {result.text || '(Пустой результат — возможно, аудио не содержит речи)'}
              </p>
            </div>
          ) : (
            <div className="bg-red-500/10 rounded-xl p-4">
              <p className="text-red-300 text-sm">{result.error}</p>
            </div>
          )}

          {/* Расшифровка с таймкодами (сегменты SpeechKit rawResults) */}
          {result.status === 'success' && result.segments && result.segments.length > 0 && (
            <details className="mt-3" open={result.segments.length <= 20}>
              <summary className="text-gray-400 text-xs cursor-pointer hover:text-gray-200 transition-colors flex items-center gap-2">
                <i className="fas fa-clock"></i>
                Расшифровка с таймкодами ({result.segments.length} сегментов)
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    navigator.clipboard.writeText(
                      result.segments!.map((s) => `[${fmtTime(s.startTime)}] ${s.text}`).join('\n')
                    );
                  }}
                  className="text-gray-500 hover:text-white transition-colors ml-1"
                  title="Копировать расшифровку с таймкодами"
                >
                  <i className="fas fa-copy"></i>
                </button>
              </summary>
              <TranscriptSegments segments={result.segments} />
            </details>
          )}

          {/* Список заказа, разобранный YandexGPT из расшифровки */}
          {result.status === 'success' && result.orderItems && result.orderItems.length > 0 && (
            <div>
              <p className="text-green-400 text-xs font-semibold uppercase tracking-wide mt-4 flex items-center gap-2">
                <i className="fas fa-list-check"></i>
                Список заказа ({result.orderItems.length})
              </p>
              <OrderItemsTable items={result.orderItems} />
            </div>
          )}
          {result.status === 'success' && result.llmError && (
            <div className="mt-3 bg-amber-500/10 border border-amber-500/20 rounded-xl p-3">
              <p className="text-amber-300 text-xs">
                ⚠️ Не удалось разобрать заказ через YandexGPT: {result.llmError}
              </p>
            </div>
          )}

          {result.rawResponse && (
            <details className="mt-3">
              <summary className="text-gray-500 text-xs cursor-pointer hover:text-gray-300 transition-colors">
                Показать raw ответ API
              </summary>
              <pre className="mt-2 bg-black/30 rounded-lg p-3 text-xs text-gray-400 overflow-x-auto">
                {JSON.stringify(result.rawResponse, null, 2)}
              </pre>
            </details>
          )}
        </div>
      ))}
    </div>
  );
}
