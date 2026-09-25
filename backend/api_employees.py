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
        data = {k: v for k, v in (request.json or {}).items()
                if k in ('name', 'email', 'phone', 'position')}
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


# ==================== ОПЦИИ РАЗБОРА ЗАКАЗОВ ====================

@employees_bp.route('/employees/<employee_id>/order-settings', methods=['GET'])
def get_order_settings(employee_id):
    """Опции разбора филиала и значения по умолчанию"""
    from order_settings import DEFAULTS
    employee = EmployeeRepository.get_by_id(employee_id)
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404
    return jsonify({'settings': employee.get_order_settings(), 'defaults': DEFAULTS})


@employees_bp.route('/employees/<employee_id>/order-settings', methods=['PUT'])
def update_order_settings(employee_id):
    """Сохранить опции разбора: неизвестные ключи и неверные значения отбрасываются"""
    from order_settings import clean, dumps
    employee = EmployeeRepository.get_by_id(employee_id)
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404
    merged = dict(employee.get_order_settings(), **(request.json or {}))
    EmployeeRepository.update(employee_id, order_settings=dumps(merged))
    return jsonify({'settings': clean(merged)})


@employees_bp.route('/employees/<employee_id>/nomenclature/<nomenclature_id>/limit', methods=['PUT'])
def update_nomenclature_limit(employee_id, nomenclature_id):
    """Реалистичный максимум количества для одной позиции (null — лимит филиала)"""
    value = (request.json or {}).get('max_quantity')
    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0):
        return jsonify({'error': 'max_quantity должен быть положительным числом или null'}), 400
    item = NomenclatureRepository.set_max_quantity(employee_id, nomenclature_id,
                                                   None if value is None else float(value))
    if not item:
        return jsonify({'error': 'Nomenclature not found'}), 404
    return jsonify(item.to_dict())


# ==================== НОМЕНКЛАТУРА ====================

@employees_bp.route('/employees/<employee_id>/nomenclature', methods=['GET'])
def get_nomenclature(employee_id):
    """Получить номенклатуру сотрудника с вариантами произношения"""
    try:
        print(f"\n📦 [API] GET /employees/{employee_id}/nomenclature")
        
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            print(f"❌ [API] Сотрудник не найден: {employee_id}")
            return jsonify({'error': 'Employee not found'}), 404
        
        print(f"✅ [API] Сотрудник найден: {employee.name}")
        
        nomenclature = NomenclatureRepository.get_by_employee(employee_id)
        print(f"✅ [API] Найдено номенклатуры: {len(nomenclature)}")
        
        # Получаем варианты для каждого элемента
        result = []
        
        # Получаем все записи словаря для этого сотрудника напрямую из БД
        from models_db import VoiceDictionary
        from database import get_session, close_session
        session = get_session()
        try:
            all_dict_entries = session.query(VoiceDictionary).filter(
                VoiceDictionary.employee_id == employee_id,
                VoiceDictionary.category == 'nomenclature'
            ).all()
            
            # Создаем словарь для быстрого поиска: {original_name: entry}
            dict_map = {entry.original: entry for entry in all_dict_entries}
            
            for n in nomenclature:
                n_dict = n.to_dict()
                
                # Ищем запись для этой номенклатуры
                dict_entry = dict_map.get(n.name)
                
                if dict_entry:
                    n_dict['variants'] = [v.to_dict() for v in dict_entry.variants]
                    print(f"   ✅ {n.name}: {len(dict_entry.variants)} вариантов")
                else:
                    n_dict['variants'] = []
                    print(f"   ⚠️  {n.name}: нет вариантов")
                
                result.append(n_dict)
        finally:
            close_session()
        
        print(f"✅ [API] Возвращаем {len(result)} элементов")
        
        return jsonify({
            'employee_id': employee_id,
            'nomenclature': result,
            'total': len(result)
        })
    except Exception as e:
        print(f"❌ [API] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@employees_bp.route('/employees/<employee_id>/nomenclature/validation', methods=['GET'])
def validate_nomenclature(employee_id):
    """Проблемы справочника, из-за которых заказ нельзя разобрать однозначно"""
    try:
        if not EmployeeRepository.get_by_id(employee_id):
            return jsonify({'error': 'Employee not found'}), 404
        from branch_data import validation
        return jsonify(validation(employee_id))
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
            try:
                from branch_data import validation
                result['validation'] = validation(employee_id)
            except Exception as exc:  # the import itself succeeded
                result['validation_error'] = str(exc)
            
            return jsonify(result)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== КЛИЕНТЫ ====================

@employees_bp.route('/employees/<employee_id>/clients', methods=['GET'])
def get_clients(employee_id):
    """Получить клиентов сотрудника с вариантами произношения"""
    try:
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        clients = ClientRepository.get_by_employee(employee_id)
        
        # Получаем варианты для каждого клиента
        result = []
        
        # Получаем все записи словаря для клиентов напрямую из БД
        from models_db import VoiceDictionary
        from database import get_session, close_session
        session = get_session()
        try:
            all_dict_entries = session.query(VoiceDictionary).filter(
                VoiceDictionary.employee_id == employee_id,
                VoiceDictionary.category == 'client'
            ).all()
            
            # Создаем словарь для быстрого поиска
            dict_map = {entry.original: entry for entry in all_dict_entries}
            
            for c in clients:
                c_dict = c.to_dict()
                dict_entry = dict_map.get(c.name)
                
                if dict_entry:
                    c_dict['variants'] = [v.to_dict() for v in dict_entry.variants]
                else:
                    c_dict['variants'] = []
                result.append(c_dict)
        finally:
            close_session()
        
        return jsonify({
            'employee_id': employee_id,
            'clients': result,
            'total': len(result)
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
            try:
                from branch_data import validation
                result['validation'] = validation(employee_id)
            except Exception as exc:  # the import itself succeeded
                result['validation_error'] = str(exc)
            
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


@employees_bp.route('/employees/<employee_id>/dictionary/variant/<int:variant_id>', methods=['DELETE'])
def delete_dictionary_variant(employee_id, variant_id):
    """Удалить вариант произношения"""
    try:
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        success = VoiceDictionaryRepository.delete_variant(variant_id)
        
        if not success:
            return jsonify({'error': 'Variant not found'}), 404
        
        return jsonify({'message': 'Variant deleted'})
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


# ==================== ЕДИНИЦЫ ИЗМЕРЕНИЯ ====================

@employees_bp.route('/employees/<employee_id>/units', methods=['GET'])
def get_units(employee_id):
    """Получить единицы измерения сотрудника"""
    try:
        from repositories import UnitOfMeasureRepository
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        units = UnitOfMeasureRepository.get_by_employee(employee_id)
        
        return jsonify({
            'employee_id': employee_id,
            'units': [u.to_dict() for u in units],
            'total': len(units)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@employees_bp.route('/employees/<employee_id>/units', methods=['POST'])
def create_unit(employee_id):
    """Создать единицу измерения"""
    try:
        from repositories import UnitOfMeasureRepository
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        data = request.json
        unit = UnitOfMeasureRepository.create({
            'employee_id': employee_id,
            'name': data.get('name'),
            'abbreviation': data.get('abbreviation'),
            'category': data.get('category')
        })
        
        return jsonify(unit.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@employees_bp.route('/employees/<employee_id>/units/<unit_id>/variants', methods=['POST'])
def add_unit_variant(employee_id, unit_id):
    """Добавить вариант произношения единицы измерения"""
    try:
        from repositories import UnitOfMeasureRepository
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        data = request.json
        variant = UnitOfMeasureRepository.add_variant(
            unit_id=unit_id,
            variant=data.get('variant'),
            confidence=data.get('confidence', 1.0)
        )
        
        return jsonify(variant.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@employees_bp.route('/employees/<employee_id>/units/<unit_id>/variants/<int:variant_id>', methods=['DELETE'])
def delete_unit_variant(employee_id, unit_id, variant_id):
    """Удалить вариант произношения единицы измерения"""
    try:
        from repositories import UnitOfMeasureRepository
        employee = EmployeeRepository.get_by_id(employee_id)
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        success = UnitOfMeasureRepository.delete_variant(variant_id)
        
        if not success:
            return jsonify({'error': 'Variant not found'}), 404
        
        return jsonify({'message': 'Variant deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
