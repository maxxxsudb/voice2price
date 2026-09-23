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

export interface YandexCloudConfig {
  apiKey: string;          // API-ключ сервисного аккаунта SpeechKit (AQVN...)
  folderId: string;        // Folder ID для SpeechKit (b1g...)
  bucketName: string;      // Имя бакета Object Storage
  accessKeyId: string;     // S3 Access Key (YCAJE...)
  secretAccessKey: string; // S3 Secret Key (YCONF...)
}

export interface RecognitionResult {
  fileId: string;
  fileName: string;
  text: string;
  confidence: number;
  status: 'success' | 'error';
  error?: string;
  rawResponse?: any;
}

export interface NomenclatureMatch {
  term: string;
  fileName: string;
  context: string;
  position: number;
}
