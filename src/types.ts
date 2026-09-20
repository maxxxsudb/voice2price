export interface AppConfig {
  apiKey: string;
  folderId: string;
  audioDir: string;
  language: string;
  model: string;
  nomenclatureTerms: string[];
  outputDir: string;
  useFuzzySearch: boolean;
  fuzzyThreshold: number;
  exportJson: boolean;
  exportTxt: boolean;
  exportCsv: boolean;
}

export interface AudioFileInfo {
  name: string;
  size: number;
  duration?: number;
  sampleRate?: number;
  channels?: number;
}

export interface RecognitionResult {
  fileName: string;
  text: string;
  status: 'success' | 'error';
  error?: string;
}
