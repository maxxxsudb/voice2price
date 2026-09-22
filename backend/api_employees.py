"""
API endpoints для работы с сотрудниками, номенклатурой и клиентами.
"""

import os
import tempfile
from pathlib import Path
from flask import Blueprint, request, jsonify
from repositories import (
    EmployeeRepository, NomenclatureRepository, 
    ClientRepository, VoiceDictionaryRepository, OrderRepository
)

employees_bp = Blueprint('employees', __name__)


# ==================== СОТРУДНИКИ ====================

@employees_bp.route('/employees', methods=['GET'])
def list_employees():
    """Список всех сотрудников"""
    try:
        employees = EmployeeRepository.get_all()
        result = []
        
        for emp in employees:
            # Считаем количество связанных данных
            nomenclature_count = len(NomenclatureRepository.get_by_employee(emp.id))
            clients_count = len(ClientRepository.get_by_employee(emp.id))
            
            result.append({
                'id': emp.id,
                'name': emp.name,
                'email': emp.email,
                'phone': emp.phone,
                'position': emp.position,
                'nomenclature_count': nomenclature_count,
                'clients_count': clients_count,
                'created_at': emp.created_at.isoformat() if emp.created_at else None,
            })
        
        return jsonify({'employees': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@employees_bp.route('/employees', methods=['POST'])
def create_employee():
    """Создать сотрудника"""
    try:
        data = request.json
        employee_id = data.get('id')
        name = data.get('name')
        
        if not employee_id or not name:
            return jsonify({'error': 'id and name are required'}), 400
        
        # Проверяем что сотрудник не существует
        existing = EmployeeRepository.get_by_id(employee_id)
        if existing:
            return jsonify({'error': f'Employee {employee_id} already exists'}), 400
        
        employee = EmployeeRepository.create(
            employee_id=employee_id,
            name=name,
            email=data.get('email'),
            phone=data.get('phone'),
            position=data.get('position')
        )
        
        return jsonify(employee.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@employees_bp.route('/employees/<employee_id>', methods=['GET'])
def get_employee(employee_id):
    """Получить информацию о сотруднике"""
    try:
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        # Получаем связанные данные
        nomenclature = NomenclatureRepository.get_by_employee(employee_id)
        clients = ClientRepository.get_by_employee(employee_id)
        
        result = employee.to_dict()
        result['nomenclature_count'] = len(nomenclature)
        result['clients_count'] = len(clients)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@employees_bp.route('/employees/<employee_id>', methods=['PUT'])
def update_employee(employee_id):
    """Обновить сотрудника"""
    try:
        data = request.json
        employee = EmployeeRepository.update(employee_id, **data)
        
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        return jsonify(employee.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@employees_bp.route('/employees/<employee_id>', methods=['DELETE'])
def delete_employee(employee_id):
    """Удалить сотрудника"""
    try:
        success = EmployeeRepository.delete(employee_id)
        if not success:
            return jsonify({'error': 'Employee not found'}), 404
        
        return jsonify({'message': 'Employee deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== НОМЕНКЛАТУРА ====================

@employees_bp.route('/employees/<employee_id>/nomenclature', methods=['GET'])
def get_nomenclature(employee_id):
    """Получить номенклатуру сотрудника"""
    try:
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        nomenclature = NomenclatureRepository.get_by_employee(employee_id)
        return jsonify({
            'employee_id': employee_id,
            'nomenclature': [n.to_dict() for n in nomenclature],
            'total': len(nomenclature)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@employees_bp.route('/employees/<employee_id>/nomenclature/import', methods=['POST'])
def import_nomenclature(employee_id):
    """Импортировать номенклатуру из XLSX"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if not file.filename.lower().endswith('.xlsx'):
            return jsonify({'error': 'File must be .xlsx'}), 400
        
        # Проверяем что сотрудник существует
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        # Сохраняем файл во временный
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            # Импортируем
            from import_nomenclature_db import import_nomenclature as do_import
            result = do_import(employee_id, tmp_path)
            
            return jsonify(result)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== КЛИЕНТЫ ====================

@employees_bp.route('/employees/<employee_id>/clients', methods=['GET'])
def get_clients(employee_id):
    """Получить клиентов сотрудника"""
    try:
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        clients = ClientRepository.get_by_employee(employee_id)
        return jsonify({
            'employee_id': employee_id,
            'clients': [c.to_dict() for c in clients],
            'total': len(clients)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@employees_bp.route('/employees/<employee_id>/clients/import', methods=['POST'])
def import_clients(employee_id):
    """Импортировать клиентов из XLSX"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if not file.filename.lower().endswith('.xlsx'):
            return jsonify({'error': 'File must be .xlsx'}), 400
        
        # Проверяем что сотрудник существует
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        # Сохраняем файл во временный
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            # Импортируем
            from import_clients_db import import_clients as do_import
            result = do_import(employee_id, tmp_path)
            
            return jsonify(result)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== СЛОВАРЬ ====================

@employees_bp.route('/employees/<employee_id>/dictionary', methods=['GET'])
def get_dictionary(employee_id):
    """Получить словарь сотрудника"""
    try:
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        entries = VoiceDictionaryRepository.get_by_employee(employee_id)
        
        return jsonify({
            'employee_id': employee_id,
            'entries': [e.to_dict() for e in entries],
            'total_entries': len(entries),
            'total_terms': len(VoiceDictionaryRepository.get_all_terms(employee_id)),
            'speechkit_format': VoiceDictionaryRepository.get_speechkit_format(employee_id)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@employees_bp.route('/employees/<employee_id>/dictionary/add', methods=['POST'])
def add_dictionary_entry(employee_id):
    """Добавить запись в словарь"""
    try:
        data = request.json
        original = data.get('original')
        variant = data.get('variant')
        category = data.get('category')
        
        if not original or not variant or not category:
            return jsonify({'error': 'original, variant and category are required'}), 400
        
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        # Создаем или находим запись
        entry = VoiceDictionaryRepository.create(
            employee_id=employee_id,
            original=original,
            category=category
        )
        
        # Добавляем вариант
        VoiceDictionaryRepository.add_variant(entry.id, variant)
        
        return jsonify({'message': 'Variant added', 'entry': entry.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== ЗАКАЗЫ ====================

@employees_bp.route('/employees/<employee_id>/orders', methods=['GET'])
def get_orders(employee_id):
    """Получить заказы сотрудника"""
    try:
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        orders = OrderRepository.get_by_employee(employee_id)
        
        return jsonify({
            'employee_id': employee_id,
            'orders': [o.to_dict() for o in orders],
            'total': len(orders)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
