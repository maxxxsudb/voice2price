import { useState, useEffect, useRef } from 'react';
import NomenclatureItem from './NomenclatureItem';
import ClientItem from './ClientItem';
import UnitItem from './UnitItem';
import CatalogValidationPanel from './CatalogValidationPanel';
import OrderSettingsPanel from './OrderSettingsPanel';

import { API } from '../api';

interface EmployeeDetail {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  position?: string;
  nomenclature_count: number;
  clients_count: number;
  created_at?: string;
}

interface Props {
  employeeId: string;
}

type TabType = 'nomenclature' | 'clients' | 'units' | 'dictionary' | 'settings' | 'import';

export default function EmployeeDetail({ employeeId }: Props) {
  const [employee, setEmployee] = useState<EmployeeDetail | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('nomenclature');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Данные для табов
  const [nomenclature, setNomenclature] = useState<any[]>([]);
  const [clients, setClients] = useState<any[]>([]);
  const [voiceConflicts, setVoiceConflicts] = useState<{ said: string; clients: { id: string; name: string }[] }[]>([]);
  const [dictionary, setDictionary] = useState<any[]>([]);
  const [units, setUnits] = useState<any[]>([]);

  // Импорт
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);
  // Перепроверить справочник после импорта или правки вариантов
  const [validationKey, setValidationKey] = useState(0);
  const revalidate = () => setValidationKey(key => key + 1);
  const nomenclatureInputRef = useRef<HTMLInputElement>(null);
  const clientsInputRef = useRef<HTMLInputElement>(null);

  // Словарь
  const [showAddVariant, setShowAddVariant] = useState(false);
  const [newVariant, setNewVariant] = useState({ original: '', variant: '', category: 'nomenclature' });

  const fetchEmployee = async () => {
    try {
      setLoading(true);
      const response = await fetch(API.employee(employeeId));
      if (!response.ok) throw new Error('Failed to fetch employee');
      const data = await response.json();
      setEmployee(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const fetchNomenclature = async () => {
    console.log(`\n📦 [FRONTEND] Загрузка номенклатуры для филиала: ${employeeId}`);
    try {
      const response = await fetch(API.employeeNomenclature(employeeId));
      console.log(`📥 [FRONTEND] Статус ответа: ${response.status}`);
      
      if (!response.ok) throw new Error('Failed to fetch nomenclature');
      
      const data = await response.json();
      console.log(`✅ [FRONTEND] Получено номенклатуры: ${data.nomenclature?.length || 0}`);
      
      if (data.nomenclature && data.nomenclature.length > 0) {
        console.log(`📋 [FRONTEND] Первая запись:`, data.nomenclature[0]);
      }
      
      setNomenclature(data.nomenclature || []);
    } catch (err) {
      console.error('❌ [FRONTEND] Ошибка загрузки номенклатуры:', err);
    }
  };

  const fetchClients = async () => {
    try {
      const response = await fetch(API.employeeClients(employeeId));
      if (!response.ok) throw new Error('Failed to fetch clients');
      const data = await response.json();
      setClients(data.clients || []);
      setVoiceConflicts(data.voice_conflicts || []);
    } catch (err) {
      console.error('Failed to fetch clients:', err);
    }
  };

  const fetchDictionary = async () => {
    try {
      const response = await fetch(API.employeeDictionary(employeeId));
      if (!response.ok) throw new Error('Failed to fetch dictionary');
      const data = await response.json();
      setDictionary(data.entries || []);
    } catch (err) {
      console.error('Failed to fetch dictionary:', err);
    }
  };

  const fetchUnits = async () => {
    try {
      const response = await fetch(API.employeeUnits(employeeId));
      if (!response.ok) throw new Error('Failed to fetch units');
      const data = await response.json();
      setUnits(data.units || []);
    } catch (err) {
      console.error('Failed to fetch units:', err);
    }
  };

  useEffect(() => {
    fetchEmployee();
    fetchNomenclature();
    fetchClients();
    fetchDictionary();
    fetchUnits();
  }, [employeeId]);

  const handleImportNomenclature = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setImportResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(API.employeeNomenclatureImport(employeeId), {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Import failed');
      }

      const result = await response.json();
      setImportResult(result);

      // Обновляем данные
      await fetchEmployee();
      await fetchNomenclature();
      await fetchDictionary();
      revalidate();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Import failed');
    } finally {
      setImporting(false);
      if (nomenclatureInputRef.current) {
        nomenclatureInputRef.current.value = '';
      }
    }
  };

  const handleImportClients = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setImportResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(API.employeeClientsImport(employeeId), {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Import failed');
      }

      const result = await response.json();
      setImportResult(result);

      // Обновляем данные
      await fetchEmployee();
      await fetchClients();
      await fetchDictionary();
      revalidate();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Import failed');
    } finally {
      setImporting(false);
      if (clientsInputRef.current) {
        clientsInputRef.current.value = '';
      }
    }
  };

  const handleAddVariant = async () => {
    if (!newVariant.original || !newVariant.variant || !newVariant.category) {
      alert('Все поля обязательны');
      return;
    }

    try {
      const response = await fetch(API.employeeDictionaryAdd(employeeId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newVariant),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to add variant');
      }

      await fetchDictionary();
      setShowAddVariant(false);
      setNewVariant({ original: '', variant: '', category: 'nomenclature' });
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to add variant');
    }
  };

  if (loading) {
    return (
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <div className="flex items-center justify-center py-12">
          <i className="fas fa-spinner fa-spin text-2xl text-gray-400"></i>
          <span className="ml-3 text-gray-400">Загрузка...</span>
        </div>
      </div>
    );
  }

  if (error || !employee) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-6">
        <p className="text-red-300">
          <i className="fas fa-exclamation-circle mr-2"></i>
          Ошибка: {error || 'Филиал не найден'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Информация о филиале (руководителе филиала) */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white text-2xl font-bold">
            {employee.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <h2 className="text-white text-xl font-bold">{employee.name}</h2>
            <p className="text-gray-400 text-sm">
              ID: {employee.id}
              {employee.position && ` • ${employee.position}`}
            </p>
            {employee.email && <p className="text-gray-400 text-sm">{employee.email}</p>}
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white/5 rounded-xl p-3 text-center">
            <p className="text-gray-400 text-xs">Номенклатура</p>
            <p className="text-white text-2xl font-bold">{employee.nomenclature_count}</p>
          </div>
          <div className="bg-white/5 rounded-xl p-3 text-center">
            <p className="text-gray-400 text-xs">Клиенты</p>
            <p className="text-white text-2xl font-bold">{employee.clients_count}</p>
          </div>
          <div className="bg-white/5 rounded-xl p-3 text-center">
            <p className="text-gray-400 text-xs">Словарь</p>
            <p className="text-white text-2xl font-bold">{dictionary.length}</p>
          </div>
          <div className="bg-white/5 rounded-xl p-3 text-center">
            <p className="text-gray-400 text-xs">Создан</p>
            <p className="text-white text-sm">
              {employee.created_at ? new Date(employee.created_at).toLocaleDateString('ru-RU') : '—'}
            </p>
          </div>
        </div>
      </div>

      {/* Табы */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <div className="flex flex-wrap gap-2 mb-6 border-b border-white/10 pb-4">
          <button
            onClick={() => setActiveTab('nomenclature')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
              activeTab === 'nomenclature'
                ? 'bg-yellow-500/20 text-yellow-300'
                : 'bg-white/5 text-gray-400 hover:bg-white/10'
            }`}
          >
            <i className="fas fa-box"></i>
            Номенклатура ({nomenclature.length})
          </button>
          <button
            onClick={() => setActiveTab('clients')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
              activeTab === 'clients'
                ? 'bg-green-500/20 text-green-300'
                : 'bg-white/5 text-gray-400 hover:bg-white/10'
            }`}
          >
            <i className="fas fa-user-tie"></i>
            Клиенты ({clients.length})
          </button>
          <button
            onClick={() => setActiveTab('units')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
              activeTab === 'units'
                ? 'bg-cyan-500/20 text-cyan-300'
                : 'bg-white/5 text-gray-400 hover:bg-white/10'
            }`}
          >
            <i className="fas fa-weight-hanging"></i>
            Ед. измерения ({units.length})
          </button>
          <button
            onClick={() => setActiveTab('dictionary')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
              activeTab === 'dictionary'
                ? 'bg-purple-500/20 text-purple-300'
                : 'bg-white/5 text-gray-400 hover:bg-white/10'
            }`}
          >
            <i className="fas fa-book"></i>
            Словарь ({dictionary.length})
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
              activeTab === 'settings'
                ? 'bg-orange-500/20 text-orange-300'
                : 'bg-white/5 text-gray-400 hover:bg-white/10'
            }`}
          >
            <i className="fas fa-sliders"></i>
            Настройки разбора
          </button>
          <button
            onClick={() => setActiveTab('import')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
              activeTab === 'import'
                ? 'bg-blue-500/20 text-blue-300'
                : 'bg-white/5 text-gray-400 hover:bg-white/10'
            }`}
          >
            <i className="fas fa-upload"></i>
            Импорт
          </button>
        </div>

        {/* Контент табов */}
        {activeTab === 'nomenclature' && (
          <div>
            <div className="mb-4 flex items-center justify-between">
              <p className="text-gray-400 text-sm">
                <i className="fas fa-info-circle mr-2"></i>
                Кликните на товар чтобы развернуть и редактировать варианты
              </p>
              <button
                onClick={() => { fetchNomenclature(); revalidate(); }}
                className="px-3 py-1 rounded-lg bg-white/5 text-gray-300 text-sm hover:bg-white/10 transition-colors"
                title="Обновить список"
              >
                <i className="fas fa-sync-alt"></i>
              </button>
            </div>
            {nomenclature.length > 0 && (
              <div className="mb-4">
                <CatalogValidationPanel employeeId={employeeId} refreshKey={validationKey} />
              </div>
            )}
            
            {nomenclature.length === 0 ? (
              <div className="text-center py-12 bg-white/5 rounded-xl border border-white/10">
                <i className="fas fa-box text-4xl text-gray-600 mb-3"></i>
                <p className="text-gray-400">Номенклатура не импортирована</p>
                <p className="text-gray-500 text-sm mt-1">Перейдите на вкладку "Импорт"</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {nomenclature.map((item) => (
                  <NomenclatureItem 
                    key={item.id} 
                    item={item} 
                    employeeId={employeeId}
                    onVariantAdded={() => {
                      fetchNomenclature();
                      fetchDictionary();
                      revalidate();
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'clients' && (
          <div>
            <div className="mb-4 flex items-center justify-between">
              <p className="text-gray-400 text-sm">
                <i className="fas fa-info-circle mr-2"></i>
                Клиент определяется по фамилии или названию; город и улица подтверждают выбор.
                Добавьте сокращение («магазин у дома», «Нурыев Лениногорск»), если клиента называют иначе.
              </p>
              <button
                onClick={fetchClients}
                className="px-3 py-1 rounded-lg bg-white/5 text-gray-300 text-sm hover:bg-white/10 transition-colors"
                title="Обновить список"
              >
                <i className="fas fa-sync-alt"></i>
              </button>
            </div>
            
            {voiceConflicts.length > 0 && (
              <details className="mb-4 rounded-xl border border-amber-400/30 bg-amber-500/10 p-3">
                <summary className="cursor-pointer text-amber-100 text-sm">
                  {voiceConflicts.length} назван{voiceConflicts.length === 1 ? 'ие подходит' : 'ия подходят'} нескольким клиентам —
                  без города/улицы или сокращения такой клиент уйдёт на проверку
                </summary>
                <ul className="mt-2 space-y-1 text-xs text-gray-100">
                  {voiceConflicts.map(conflict => (
                    <li key={conflict.said}>
                      «{conflict.said}»: {conflict.clients.map(c => c.name).join('; ')}
                    </li>
                  ))}
                </ul>
              </details>
            )}

            {clients.length === 0 ? (
              <div className="text-center py-12 bg-white/5 rounded-xl border border-white/10">
                <i className="fas fa-user-tie text-4xl text-gray-600 mb-3"></i>
                <p className="text-gray-400">Клиенты не импортированы</p>
                <p className="text-gray-500 text-sm mt-1">Перейдите на вкладку "Импорт"</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {clients.map((client) => (
                  <ClientItem 
                    key={client.id} 
                    client={client} 
                    employeeId={employeeId}
                    onVariantAdded={() => {
                      fetchClients();
                      fetchDictionary();
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'units' && (
          <div>
            <div className="mb-4 flex items-center justify-between">
              <p className="text-gray-400 text-sm">
                <i className="fas fa-info-circle mr-2"></i>
                Кликните на единицу чтобы развернуть и редактировать варианты
              </p>
              <button
                onClick={fetchUnits}
                className="px-3 py-1 rounded-lg bg-white/5 text-gray-300 text-sm hover:bg-white/10 transition-colors"
                title="Обновить список"
              >
                <i className="fas fa-sync-alt"></i>
              </button>
            </div>
            
            {units.length === 0 ? (
              <div className="text-center py-12 bg-white/5 rounded-xl border border-white/10">
                <i className="fas fa-weight-hanging text-4xl text-gray-600 mb-3"></i>
                <p className="text-gray-400">Единицы измерения не добавлены</p>
                <p className="text-gray-500 text-sm mt-1">Добавьте единицы измерения для заказов</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {units.map((unit) => (
                  <UnitItem 
                    key={unit.id} 
                    unit={unit} 
                    employeeId={employeeId}
                    onVariantAdded={fetchUnits}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'settings' && <OrderSettingsPanel employeeId={employeeId} />}

        {activeTab === 'dictionary' && (
          <div>
            <div className="flex justify-end mb-4">
              <button
                onClick={() => setShowAddVariant(!showAddVariant)}
                className="px-4 py-2 rounded-lg bg-purple-500/20 text-purple-300 text-sm font-medium hover:bg-purple-500/30 transition-colors flex items-center gap-2"
              >
                <i className={`fas fa-${showAddVariant ? 'times' : 'plus'}`}></i>
                {showAddVariant ? 'Отмена' : 'Добавить вариант'}
              </button>
            </div>

            {showAddVariant && (
              <div className="bg-white/5 rounded-xl p-4 mb-4 border border-white/10">
                <h4 className="text-white font-medium mb-3">Добавить голосовой вариант</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <input
                    type="text"
                    placeholder="Оригинальное название"
                    value={newVariant.original}
                    onChange={(e) => setNewVariant({ ...newVariant, original: e.target.value })}
                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-purple-400/50"
                  />
                  <input
                    type="text"
                    placeholder="Вариант произношения"
                    value={newVariant.variant}
                    onChange={(e) => setNewVariant({ ...newVariant, variant: e.target.value })}
                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-purple-400/50"
                  />
                  <select
                    value={newVariant.category}
                    onChange={(e) => setNewVariant({ ...newVariant, category: e.target.value })}
                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-400/50"
                  >
                    <option value="nomenclature" className="bg-slate-800">Номенклатура</option>
                    <option value="client" className="bg-slate-800">Клиент</option>
                  </select>
                </div>
                <button
                  onClick={handleAddVariant}
                  className="mt-3 px-4 py-2 rounded-lg bg-purple-500/20 text-purple-300 text-sm font-medium hover:bg-purple-500/30 transition-colors"
                >
                  <i className="fas fa-save mr-2"></i>
                  Сохранить
                </button>
              </div>
            )}

            {dictionary.length === 0 ? (
              <div className="text-center py-12">
                <i className="fas fa-book text-4xl text-gray-600 mb-3"></i>
                <p className="text-gray-400">Словарь пуст</p>
                <p className="text-gray-500 text-sm mt-1">Импортируйте данные или добавьте варианты вручную</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[500px] overflow-y-auto">
                {dictionary.map((entry) => (
                  <div key={entry.id} className="bg-white/5 rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <p className="text-white font-medium">{entry.original}</p>
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        entry.category === 'client' 
                          ? 'bg-green-500/20 text-green-300' 
                          : 'bg-yellow-500/20 text-yellow-300'
                      }`}>
                        {entry.category === 'client' ? 'Клиент' : 'Номенклатура'}
                      </span>
                    </div>
                    {entry.variants && entry.variants.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {entry.variants.map((v: any, idx: number) => (
                          <span key={idx} className="text-xs bg-white/10 text-gray-300 px-2 py-1 rounded">
                            {v.variant}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'import' && (
          <div className="space-y-6">
            {/* Импорт номенклатуры */}
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4">
              <h4 className="text-yellow-300 font-semibold mb-3 flex items-center gap-2">
                <i className="fas fa-box"></i>
                Импорт номенклатуры
              </h4>
              <input
                ref={nomenclatureInputRef}
                type="file"
                accept=".xlsx"
                onChange={handleImportNomenclature}
                disabled={importing}
                className="hidden"
                id="nomenclature-import"
              />
              <label
                htmlFor="nomenclature-import"
                className={`inline-block px-4 py-2 rounded-lg text-sm font-medium cursor-pointer transition-colors ${
                  importing
                    ? 'bg-gray-500/20 text-gray-400 cursor-not-allowed'
                    : 'bg-yellow-500/20 text-yellow-300 hover:bg-yellow-500/30'
                }`}
              >
                <i className="fas fa-upload mr-2"></i>
                {importing ? 'Импорт...' : 'Выбрать XLSX файл'}
              </label>
              <p className="text-gray-400 text-xs mt-2">
                Файл должен содержать колонки: Наименование, Артикул, Код, Вес и т.д.
              </p>
            </div>

            {/* Импорт клиентов */}
            <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4">
              <h4 className="text-green-300 font-semibold mb-3 flex items-center gap-2">
                <i className="fas fa-user-tie"></i>
                Импорт клиентов
              </h4>
              <input
                ref={clientsInputRef}
                type="file"
                accept=".xlsx"
                onChange={handleImportClients}
                disabled={importing}
                className="hidden"
                id="clients-import"
              />
              <label
                htmlFor="clients-import"
                className={`inline-block px-4 py-2 rounded-lg text-sm font-medium cursor-pointer transition-colors ${
                  importing
                    ? 'bg-gray-500/20 text-gray-400 cursor-not-allowed'
                    : 'bg-green-500/20 text-green-300 hover:bg-green-500/30'
                }`}
              >
                <i className="fas fa-upload mr-2"></i>
                {importing ? 'Импорт...' : 'Выбрать XLSX файл'}
              </label>
              <p className="text-gray-400 text-xs mt-2">
                Файл должен содержать колонки: Наименование, Код, Бизнес-регион и т.д.
              </p>
            </div>

            {/* Результат импорта */}
            {importResult && (
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
                <h4 className="text-blue-300 font-semibold mb-3 flex items-center gap-2">
                  <i className="fas fa-check-circle"></i>
                  Результат импорта
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                  <div>
                    <p className="text-gray-400">Всего строк</p>
                    <p className="text-white font-bold">{importResult.total_rows}</p>
                  </div>
                  <div>
                    <p className="text-gray-400">Успешно</p>
                    <p className="text-green-300 font-bold">{importResult.valid_rows}</p>
                  </div>
                  <div>
                    <p className="text-gray-400">Ошибок</p>
                    <p className="text-red-300 font-bold">{importResult.invalid_rows}</p>
                  </div>
                  <div>
                    <p className="text-gray-400">В словаре</p>
                    <p className="text-purple-300 font-bold">{importResult.dictionary_entries}</p>
                  </div>
                </div>
                {importResult.updated !== undefined && (
                  <p className="mt-3 text-gray-100 text-sm">
                    Повторный импорт без дублей: обновлено {importResult.updated}, новых {importResult.created},
                    {' '}вернулось {importResult.restored}, скрыто (нет в файле) {importResult.removed}.
                    Лимиты, варианты произношения и прошлые заказы сохранены.
                  </p>
                )}
              </div>
            )}
            {importResult && (
              <CatalogValidationPanel employeeId={employeeId} refreshKey={validationKey} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
