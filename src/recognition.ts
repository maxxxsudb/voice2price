import type { AudioFile, RecognitionResult } from './types';

// Publish SpeechKit text before waiting for the independent order request.
export async function recognizeFile(
  file: AudioFile,
  employeeId: string | null,
  processOrder: boolean,
  endpoints: { recognize: string; processOrder: string },
  publish: (result: RecognitionResult) => void,
  request: typeof fetch = fetch,
) {
  const base = { fileId: file.id, fileName: file.name, confidence: 0 };
  let result: RecognitionResult;
  try {
    const form = new FormData();
    form.append('file', file);
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
