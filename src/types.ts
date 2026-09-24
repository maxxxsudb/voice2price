export interface AudioFile extends File {
  id: string;
  duration?: number;
}

export interface ApiConfig {
  apiKey: string;
  folderId: string;
  language: string;
  model: string;
}

export const DEFAULT_ORDER_PROMPT = `Ты — ассистент по обработке заказов медицинской номенклатуры.
Из текста заказа извлеки каждую позицию и верни ТОЛЬКО валидный JSON
массив объектов со строгими полями:
- "name": название товара (нормализованное, как в номенклатуре)
- "nomenclature_id": ID однозначно найденного товара из каталога или null
- "quantity": количество (число или null)
- "unit": единица измерения из заказа или null
- "needs_review": требуется ли уточнение (boolean)
- "review_reason": причина уточнения или пустая строка
Если количество не указано или неоднозначно — верни null, не придумывай его.
Никакого текста вне JSON, только массив.`;

export interface YandexCloudConfig {
  hasApiKey?: boolean;
  hasSecretAccessKey?: boolean;
  apiKey: string;          // API-ключ сервисного аккаунта SpeechKit/YandexGPT (AQVN...)
  folderId: string;        // Folder ID для SpeechKit (b1g...)
  bucketName: string;      // Имя бакета Object Storage
  accessKeyId: string;     // S3 Access Key (YCAJE...)
  secretAccessKey: string; // S3 Secret Key (YCONF...)
  orderPrompt?: string;    // Промт для разбора расшифровки в список заказа (YandexGPT)
  yandexModel?: string;    // Модель YandexGPT: yandexgpt-lite / yandexgpt / yandexgpt-pro
}

export interface OrderItem {
  name: string;
  nomenclature_id: string | null;
  quantity: number | null;
  needs_review: boolean;
  review_reason: string;
  unit?: string | null;
}

// Сегмент расшифровки SpeechKit с таймкодами (rawResults=true)
export interface TranscriptSegment {
  startTime?: string;   // напр. "0.00s" или "12.345s"
  endTime?: string;
  text: string;
  words?: { word?: string; startTime?: string; endTime?: string; confidence?: number }[];
}

export interface RecognitionResult {
  fileId: string;
  fileName: string;
  text: string;
  confidence: number;
  status: 'success' | 'error';
  error?: string;
  rawResponse?: any;
  segments?: TranscriptSegment[];  // расшифровка с таймкодами (этап распознавания)
  orderItems?: OrderItem[];  // список заказа, разобранный YandexGPT из расшифровки
  llmError?: string;         // ошибка разбора через YandexGPT (если был запрошен)
  llmStatus?: 'processing' | 'done' | 'error';
  resultId?: string;
}

export interface NomenclatureMatch {
  term: string;
  fileName: string;
  context: string;
  position: number;
}
