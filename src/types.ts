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
- "quantity": количество (число)
- "unit": единица измерения (шт, уп, упак, мл и т.п.)
Если количество не указано — ставь 1.
Никакого текста вне JSON, только массив.`;

export interface YandexCloudConfig {
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
  quantity: number | string;
  unit?: string;
}

export interface RecognitionResult {
  fileId: string;
  fileName: string;
  text: string;
  confidence: number;
  status: 'success' | 'error';
  error?: string;
  rawResponse?: any;
  orderItems?: OrderItem[];  // список заказа, разобранный YandexGPT из расшифровки
  llmError?: string;         // ошибка разбора через YandexGPT (если был запрошен)
}

export interface NomenclatureMatch {
  term: string;
  fileName: string;
  context: string;
  position: number;
}
