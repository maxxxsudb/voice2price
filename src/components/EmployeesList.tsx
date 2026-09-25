import { useState, useEffect } from 'react';

import { API } from '../api';

interface Employee {
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
  onSelectEmployee: (employeeId: string) => void;
  selectedEmployeeId: string | null;
}

export default function EmployeesList({ onSelectEmployee, selectedEmployeeId }: Props) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newEmployee, setNewEmployee] = useState({ id: '', name: '', email: '', phone: '', position: '' });

  const fetchEmployees = async () => {
    try {
      setLoading(true);
      const response = await fetch(API.employees);
      if (!response.ok) throw new Error('Failed to fetch employees');
      const data = await response.json();
      setEmployees(data.employees || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmployees();
  }, []);

  const handleCreate = async () => {
    if (!newEmployee.id || !newEmployee.name) {
      alert('ID и имя обязательны');
      return;
    }

    try {
      const response = await fetch(API.employees, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newEmployee),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to create employee');
      }

      await fetchEmployees();
      setShowCreateForm(false);
      setNewEmployee({ id: '', name: '', email: '', phone: '', position: '' });
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create employee');
    }
  };

  const handleDelete = async (employeeId: string) => {
    if (!confirm(`Удалить филиал ${employeeId} со справочниками?`)) return;

    try {
      const response = await fetch(API.employee(employeeId), {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to delete employee');

      await fetchEmployees();
      if (selectedEmployeeId === employeeId) {
        onSelectEmployee('');
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete employee');
    }
  };

  if (loading) {
    return (
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <div className="flex items-center justify-center py-12">
          <i className="fas fa-spinner fa-spin text-2xl text-gray-400"></i>
          <span className="ml-3 text-gray-400">Загрузка филиалов...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-6">
        <p className="text-red-300">
          <i className="fas fa-exclamation-circle mr-2"></i>
          Ошибка: {error}
        </p>
        <button
          onClick={fetchEmployees}
          className="mt-3 px-4 py-2 rounded-lg bg-red-500/20 text-red-300 text-sm hover:bg-red-500/30 transition-colors"
        >
          <i className="fas fa-redo mr-2"></i>
          Повторить
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-semibold text-lg flex items-center gap-2">
          <i className="fas fa-users text-blue-400"></i>
          Филиалы
          <span className="text-sm font-normal text-gray-400">({employees.length})</span>
        </h3>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="px-4 py-2 rounded-lg bg-blue-500/20 text-blue-300 text-sm font-medium hover:bg-blue-500/30 transition-colors flex items-center gap-2"
        >
          <i className={`fas fa-${showCreateForm ? 'times' : 'plus'}`}></i>
          {showCreateForm ? 'Отмена' : 'Добавить'}
        </button>
      </div>

      {/* Форма создания */}
      {showCreateForm && (
        <div className="bg-white/5 rounded-xl p-4 mb-4 border border-white/10">
          <h4 className="text-white font-medium mb-3">Новый филиал</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="ID филиала (например: kazan)"
              value={newEmployee.id}
              onChange={(e) => setNewEmployee({ ...newEmployee, id: e.target.value })}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-400/50"
            />
            <input
              type="text"
              placeholder="Руководитель филиала *"
              value={newEmployee.name}
              onChange={(e) => setNewEmployee({ ...newEmployee, name: e.target.value })}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-400/50"
            />
            <input
              type="email"
              placeholder="Email"
              value={newEmployee.email}
              onChange={(e) => setNewEmployee({ ...newEmployee, email: e.target.value })}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-400/50"
            />
            <input
              type="text"
              placeholder="Телефон"
              value={newEmployee.phone}
              onChange={(e) => setNewEmployee({ ...newEmployee, phone: e.target.value })}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-400/50"
            />
            <input
              type="text"
              placeholder="Название филиала / должность"
              value={newEmployee.position}
              onChange={(e) => setNewEmployee({ ...newEmployee, position: e.target.value })}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-400/50 md:col-span-2"
            />
          </div>
          <button
            onClick={handleCreate}
            className="mt-3 px-4 py-2 rounded-lg bg-blue-500/20 text-blue-300 text-sm font-medium hover:bg-blue-500/30 transition-colors"
          >
            <i className="fas fa-save mr-2"></i>
            Создать
          </button>
        </div>
      )}

      {/* Список филиалов */}
      {employees.length === 0 ? (
        <div className="text-center py-12">
          <i className="fas fa-users text-4xl text-gray-600 mb-3"></i>
          <p className="text-gray-400">Филиалы не найдены</p>
          <p className="text-gray-500 text-sm mt-1">Добавьте первый филиал</p>
        </div>
      ) : (
        <div className="space-y-2">
          {employees.map((employee) => (
            <div
              key={employee.id}
              onClick={() => onSelectEmployee(employee.id)}
              className={`rounded-xl p-4 cursor-pointer transition-all ${
                selectedEmployeeId === employee.id
                  ? 'bg-blue-500/20 border border-blue-500/30'
                  : 'bg-white/5 border border-white/10 hover:bg-white/10'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white font-bold">
                    {employee.name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <p className="text-white font-medium">{employee.name}</p>
                    <p className="text-gray-400 text-xs">
                      ID: {employee.id}
                      {employee.position && ` • ${employee.position}`}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-gray-300 text-sm">
                      <i className="fas fa-box text-yellow-400 mr-1"></i>
                      {employee.nomenclature_count}
                    </p>
                    <p className="text-gray-300 text-sm">
                      <i className="fas fa-user-tie text-green-400 mr-1"></i>
                      {employee.clients_count}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(employee.id);
                    }}
                    className="text-red-400 hover:text-red-300 transition-colors"
                  >
                    <i className="fas fa-trash"></i>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
