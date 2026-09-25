// Единая точка доступа к API бэкенда.
//
// ВАЖНО: все запросы из браузера идут ТОЛЬКО через относительные пути /api/...
//  - В Docker: браузер -> vite-dev-server (3000) -> proxy '/api' -> http://backend:5000
//    (браузер НЕ должен обращаться к http://backend:5000 напрямую — это имя хоста
//     существует только внутри docker-сети, и прямой запрос даёт "Failed to fetch")
//  - Локально без Docker: прокси Vite ведёт на VITE_BACKEND_URL (по умолчанию localhost:5000)
//
// Поэтому здесь нет никакого базового URL с портом — только относительные пути.

import type { YandexCloudConfig } from './types';

export function cloudConfigFromSettings(settings: any): YandexCloudConfig {
  return {
    apiKey: '', secretAccessKey: '',
    folderId: settings?.folder_id || '', bucketName: settings?.bucket_name || '',
    accessKeyId: settings?.access_key_id || '',
    hasApiKey: Boolean(settings?.has_api_key),
    hasSecretAccessKey: Boolean(settings?.has_secret_access_key),
    orderPrompt: settings?.order_prompt, yandexModel: settings?.yandex_model,
  };
}

export const API = {
  health: '/api/health',
  recognize: '/api/recognize',
  analyze: '/api/analyze',
  analyzeXlsx: '/api/analyze-xlsx',
  ycSettings: '/api/yandex-cloud/settings',
  ycTestConnection: '/api/yandex-cloud/test-connection',
  processOrder: '/api/process-order',
  processOrders: '/api/process-orders',
  detectClient: '/api/detect-client',
  engines: '/api/engines',
  employees: '/api/employees',
  employee: (id: string) => `/api/employees/${id}`,
  employeeNomenclature: (id: string) => `/api/employees/${id}/nomenclature`,
  employeeNomenclatureValidation: (id: string) => `/api/employees/${id}/nomenclature/validation`,
  employeeNomenclatureLimit: (id: string, nomenclatureId: string) =>
    `/api/employees/${id}/nomenclature/${nomenclatureId}/limit`,
  employeeOrderSettings: (id: string) => `/api/employees/${id}/order-settings`,
  employeeNomenclatureImport: (id: string) => `/api/employees/${id}/nomenclature/import`,
  employeeClients: (id: string) => `/api/employees/${id}/clients`,
  employeeClientsImport: (id: string) => `/api/employees/${id}/clients/import`,
  employeeDictionary: (id: string) => `/api/employees/${id}/dictionary`,
  employeeDictionaryAdd: (id: string) => `/api/employees/${id}/dictionary/add`,
  employeeDictionaryVariant: (id: string, variantId: number | string) =>
    `/api/employees/${id}/dictionary/variant/${variantId}`,
  employeeUnits: (id: string) => `/api/employees/${id}/units`,
  employeeUnitVariants: (id: string, unitId: string | number) =>
    `/api/employees/${id}/units/${unitId}/variants`,
  employeeUnitVariant: (id: string, unitId: string | number, variantId: number | string) =>
    `/api/employees/${id}/units/${unitId}/variants/${variantId}`,
};
