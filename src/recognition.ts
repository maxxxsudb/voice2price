import type { AudioFile, ParsedOrder, RecognitionResult } from './types';

// Publish SpeechKit text before waiting for the independent order request.
export async function recognizeFile(
  file: AudioFile,
  employeeId: string | null,
  processOrder: boolean,
  endpoints: { recognize: string; processOrder: string },
  publish: (result: RecognitionResult) => void,
  request: typeof fetch = fetch,
  engine?: 'speechkit' | 'gigaam',
) {
  const base = { fileId: file.id, fileName: file.name, confidence: 0 };
  let result: RecognitionResult;
  try {
    const form = new FormData();
    form.append('file', file);
    if (engine) form.append('engine', engine);
    const response = await request(endpoints.recognize, { method: 'POST', body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Ошибка распознавания: ${response.status}`);
    result = {
      ...base, status: 'success', text: data.text || '',
      confidence: data.confidence || 0, rawResponse: data,
      segments: Array.isArray(data.segments_with_timings) ? data.segments_with_timings : undefined,
      llmStatus: processOrder && data.text ? 'processing' : undefined,
    };
  } catch (error) {
    publish({ ...base, status: 'error', text: '',
      error: error instanceof Error ? error.message : 'Ошибка распознавания' });
    return;
  }
  publish(result);
  if (!processOrder || !result.text) return;
  try {
    const response = await request(endpoints.processOrder, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: result.text, employee_id: employeeId }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Ошибка разбора: ${response.status}`);
    if (!Array.isArray(data.order_items)) throw new Error('Сервер не вернул список заказа');
    publish({ ...result, llmStatus: 'done', orderItems: data.order_items });
  } catch (error) {
    publish({ ...result, llmStatus: 'error',
      llmError: error instanceof Error ? error.message : 'Ошибка разбора заказа' });
  }
}

// Recording time for merging messages: the backend reads it from the file name
// («2026-08-23 21-37-42.mp3»), lastModified is the fallback.
export async function processOrders(
  results: RecognitionResult[],
  files: { id: string; name: string; lastModified?: number }[],
  employeeId: string,
  endpoint: string,
  request: typeof fetch = fetch,
): Promise<ParsedOrder[]> {
  const messages = results
    .filter(result => result.status === 'success' && result.text.trim())
    .map(result => {
      const file = files.find(item => item.id === result.fileId);
      return { id: result.fileId, file_name: result.fileName, text: result.text,
        last_modified: file?.lastModified };
    });
  if (messages.length === 0) return [];
  const response = await request(endpoint, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_id: employeeId, messages }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Ошибка разбора: ${response.status}`);
  if (!Array.isArray(data.orders)) throw new Error('Сервер не вернул список заказов');
  return data.orders;
}
