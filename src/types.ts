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
  serviceAccountKey: string; // JSON-ключ ИЛИ PEM-приватный ключ сервисного аккаунта
  serviceAccountId: string;  // ID сервисного аккаунта (aje...) — обязателен в PEM-режиме
  folderId: string;          // Folder ID для SpeechKit
  bucketName: string;        // Имя бакета Object Storage
  accessKeyId: string;       // Access Key для Object Storage
  secretAccessKey: string;   // Secret Key для Object Storage
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
