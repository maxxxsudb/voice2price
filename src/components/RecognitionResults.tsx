import ClientTeach from './ClientTeach';
import type { RecognitionResult, OrderItem, TranscriptSegment, ParsedOrder, ClientMatch } from '../types';

interface Props {
  results: RecognitionResult[];
  onClear: () => void;
  orders?: ParsedOrder[];
  ordersStatus?: 'processing' | 'done' | 'error';
  ordersError?: string;
  ordersParser?: 'rules' | 'llm';
  employeeId?: string | null;
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
            <th className="text-left px-4 py-2 font-medium">Проверка</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i} className="border-t border-white/5">
              <td className="px-4 py-2 text-gray-500">{i + 1}</td>
              <td className="px-4 py-2 text-gray-200">
                {item.name}
                {item.nomenclature_id && <div className="text-gray-200 text-xs">ID: {item.nomenclature_id}</div>}
                {item.source_text && <div className="text-gray-400 text-xs">Сказано: «{item.source_text}»</div>}
                {item.comments && <div className="text-amber-300 text-xs">Комментарий: {item.comments}</div>}
              </td>
              <td className="px-4 py-2 text-right text-white font-medium">{String(item.quantity ?? 'Не указано')}</td>
              <td className="px-4 py-2 text-gray-200">{item.unit ?? 'Не указана'}</td>
              <td className="px-4 py-2 bg-gray-900 text-gray-100">
                {item.needs_review ? `Требует уточнения: ${item.review_reason}` : 'Сопоставлено'}
                {item.auto_note && <div className="text-amber-300 text-xs">{item.auto_note}</div>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const MATCHED_BY: Record<string, string> = {
  dictionary: 'по сокращению из словаря',
  name: 'по фамилии / названию',
  address: 'только по адресу',
};

function ClientLine({ client, employeeId }: { client: ClientMatch | null | undefined; employeeId?: string | null }) {
  if (!client) return <p className="text-gray-300 text-sm">Клиент: не определялся (филиал не выбран или нет справочника клиентов)</p>;
  const found = Boolean(client.client_id);
  const tone = !found ? 'border-white/10 bg-white/5'
    : client.needs_review ? 'border-amber-400/40 bg-amber-500/10' : 'border-emerald-400/40 bg-emerald-500/10';
  return (
    <div className={`rounded-xl border p-3 text-sm ${tone}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-gray-200 text-xs uppercase tracking-wide">Клиент</p>
          <p className="text-white font-medium">{client.public_name || client.name || 'не определён'}</p>
          {client.public_name && client.name && client.public_name !== client.name && (
            <p className="text-gray-300 text-xs">{client.name}</p>
          )}
          {client.said && found && (
            <p className="text-gray-300 text-xs">
              Сказано: «{client.said}»{client.matched_by && ` — ${MATCHED_BY[client.matched_by] ?? client.matched_by}`}
            </p>
          )}
        </div>
        {found && (
          <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${client.needs_review
            ? 'bg-amber-300 text-slate-950' : 'bg-emerald-300 text-slate-950'}`}>
            {client.needs_review ? 'Проверить' : 'Определён'}
            {typeof client.confidence === 'number' && ` · ${Math.round(client.confidence * 100)}%`}
          </span>
        )}
      </div>
      {client.needs_review && (
        <p className="mt-2 text-amber-100 text-xs">{client.review_reason}</p>
      )}
      {client.needs_review && client.candidates.length > 1 && (
        <ul className="mt-1 text-gray-100 text-xs list-disc pl-5">
          {client.candidates.map(c => (
            <li key={c.id}>{c.name}{typeof c.confidence === 'number' && ` — ${Math.round(c.confidence * 100)}%`}</li>
          ))}
        </ul>
      )}
      {client.needs_review && employeeId && <ClientTeach client={client} employeeId={employeeId} />}
    </div>
  );
}

function OrdersList({ orders, status, error, parser, employeeId }: {
  orders: ParsedOrder[]; status?: Props['ordersStatus']; error?: string; parser?: Props['ordersParser'];
  employeeId?: string | null;
}) {
  if (status === 'processing') {
    return <p role="status" className="bg-gray-900 text-gray-100 rounded-xl p-3 text-sm">Разбираю заказы…</p>;
  }
  if (status === 'error') {
    return <p role="alert" className="bg-gray-900 text-amber-200 rounded-xl p-3 text-sm">Не удалось разобрать заказы: {error}</p>;
  }
  if (!orders.length) return null;
  return (
    <div className="space-y-4">
      {orders.map((order, index) => {
        const review = order.order_items.filter(item => item.needs_review).length;
        return (
          <div key={order.message_ids.join('-')} className="bg-white/5 rounded-2xl border border-white/10 p-6">
            <h4 className="text-white font-semibold">
              Заказ {index + 1}: {order.order_items.length} поз.{review > 0 && `, на проверку ${review}`}
              {parser && (
                <span className="ml-2 align-middle rounded-full bg-white/10 px-2 py-0.5 text-xs font-normal text-gray-100">
                  {parser === 'llm' ? 'YandexGPT' : 'по справочнику'}
                </span>
              )}
            </h4>
            <p className="text-gray-400 text-xs mt-1">
              {order.merged ? `Склеено из ${order.file_names.length} сообщений: ` : 'Сообщение: '}
              {order.file_names.join(', ')}
            </p>
            {order.merge_reasons.length > 0 && (
              <ul className="mt-1 list-disc pl-5 text-gray-300 text-xs">
                {order.merge_reasons.map(reason => <li key={reason}>{reason}</li>)}
              </ul>
            )}
            <div className="mt-3"><ClientLine client={order.client} employeeId={employeeId} /></div>
            {order.order_items.length > 0
              ? <OrderItemsTable items={order.order_items} />
              : <p className="mt-3 text-gray-100">Позиции заказа не найдены.</p>}
          </div>
        );
      })}
    </div>
  );
}

export default function RecognitionResults({ results, onClear, orders = [], ordersStatus, ordersError, ordersParser, employeeId }: Props) {
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

      <OrdersList orders={orders} status={ordersStatus} error={ordersError} parser={ordersParser} employeeId={employeeId} />

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
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                    <span className={`rounded-full px-2 py-0.5 ${result.engine === 'gigaam'
                      ? 'bg-cyan-400/20 text-cyan-200' : 'bg-violet-400/20 text-violet-200'}`}>
                      {result.engine === 'gigaam' ? 'GigaAM · локально' : 'SpeechKit · облако'}
                    </span>
                    {result.engine !== 'gigaam' && result.confidence > 0 && (
                      <span className="text-gray-300">Уверенность: {(result.confidence * 100).toFixed(1)}%</span>
                    )}
                  </div>
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
              <p className="text-gray-200 text-xs uppercase tracking-wide mb-1 flex items-center gap-1">
                <i className="fas fa-microphone"></i>
                Текст распознавания
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

          {result.status === 'success' && result.client !== undefined && (
            <div className="mt-3"><ClientLine client={result.client} employeeId={employeeId} /></div>
          )}
          {result.clientError && (
            <p className="mt-3 text-amber-200 text-sm">Не удалось определить клиента: {result.clientError}</p>
          )}

          {/* Расшифровка с таймкодами */}
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

          {/* Список заказа из расшифровки */}
          {result.orderStatus === 'processing' && (
            <p role="status" className="mt-3 bg-gray-900 text-gray-100 rounded-xl p-3 text-sm">
              Расшифровка готова. Разбираю заказ…
            </p>
          )}
          {result.orderStatus === 'done' && result.orderItems?.length === 0 && (
            <p className="mt-3 text-gray-100">Позиции заказа в расшифровке не найдены.</p>
          )}
          {result.status === 'success' && result.orderItems && result.orderItems.length > 0 && (
            <div>
              <p className="text-green-400 text-xs font-semibold uppercase tracking-wide mt-4 flex items-center gap-2">
                <i className="fas fa-list-check"></i>
                Список заказа ({result.orderItems.length})
              </p>
              <OrderItemsTable items={result.orderItems} />
            </div>
          )}
          {result.status === 'success' && result.orderError && (
            <div className="mt-3 bg-amber-500/10 border border-amber-500/20 rounded-xl p-3">
              <p className="text-amber-200 text-xs">
                Не удалось разобрать заказ{result.parser === 'llm' ? ' через YandexGPT' : ''}: {result.orderError}
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
