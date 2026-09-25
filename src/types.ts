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

export const DEFAULT_ORDER_PROMPT = `Ты разбираешь голосовые заказы мясной продукции и полуфабрикатов от магазинов.
Из текста заказа извлеки каждую позицию и верни ТОЛЬКО валидный JSON-массив
объектов со строгими полями:
- "name": название товара (как в справочнике номенклатуры)
- "nomenclature_id": ID однозначно найденного товара из каталога или null
- "quantity": количество (число или null)
- "unit": единица измерения из заказа ("кг", "шт", "уп") или null
- "needs_review": требуется ли уточнение (boolean)
- "review_reason": причина уточнения или пустая строка
«Кило двести» = 1.2 кг, «два с половиной» = 2.5. Клиент, адрес, прайс и машина — не товары.
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
  spoken_name?: string;      // как сказал клиент (разбор v3)
  source_text?: string;      // цитата из расшифровки с количеством
  comments?: string;         // «только большие», «строго 2 штуки» и т.п.
  auto_note?: string;        // количество пересчитано автоматически («пятьсот» -> 0.5 кг)
}

export type SttEngine = 'gigaam' | 'speechkit';
export type OrderParser = 'rules' | 'llm';

// Готовность движков (GET /api/engines)
export interface EngineOption {
  id: string;
  ready: boolean;
  detail: string;
  missing: string[];
}

export interface EnginesInfo {
  stt: { default: SttEngine; options: EngineOption[] };
  parser: { default: OrderParser; options: EngineOption[] };
}

// Клиент, названный в сообщении (по справочнику клиентов филиала).
// confidence: 1.0 — сокращение из словаря, 0.85+ — названа фамилия/название,
// 0.35–0.45 — только город и улица (подсказка, всегда на проверку).
export interface ClientMatch {
  client_id: string | null;
  name: string | null;
  public_name?: string | null;
  code?: string | null;
  said: string;
  matched_by?: 'dictionary' | 'name' | 'address' | null;
  confidence?: number;
  needs_review: boolean;
  review_reason: string;
  candidates: { id: string; name: string; confidence?: number }[];
}

// Заказ из одного или нескольких подряд идущих голосовых одного клиента
export interface ParsedOrder {
  message_ids: string[];
  file_names: string[];
  merged: boolean;
  merge_reasons: string[];
  text: string;
  client: ClientMatch | null;
  order_items: OrderItem[];
}

// Опции разбора заказов филиала (все проверки отключаемые)
export interface OrderSettings {
  corrections: boolean;
  plausibility: boolean;
  max_kg: number | null;      // лимиты филиала; null — не заданы (проверка по лимиту позиции)
  max_pcs: number | null;
  max_packs: number | null;
  grams_over_limit: boolean;
  size_in_name: boolean;
  detect_client: boolean;
  merge_messages: boolean;
  merge_window_min: number;
}

export interface ValidationIssue {
  level: 'error' | 'warning' | 'info';
  kind: string;
  message: string;
  items: { id: string; name: string }[];
}

export interface CatalogValidation {
  issues: ValidationIssue[];
  counts: { error: number; warning: number; info: number };
  catalog_size: number;
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
  engine?: SttEngine;              // чем распознано
  client?: ClientMatch | null;     // клиент по справочнику филиала (если филиал выбран)
  clientError?: string;
  orderItems?: OrderItem[];        // список заказа из расшифровки
  orderError?: string;
  orderStatus?: 'processing' | 'done' | 'error';
  parser?: OrderParser;            // чем разобран заказ
  resultId?: string;
}

export interface NomenclatureMatch {
  term: string;
  fileName: string;
  context: string;
  position: number;
}
