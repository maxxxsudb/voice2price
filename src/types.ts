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
