#!/usr/bin/env python3
"""
Импортер номенклатуры с привязкой к сотруднику.

Использование:
    python import_nomenclature_v2.py <employee_id> <путь_к_файлу.xlsx>

Пример:
    python import_nomenclature_v2.py ivanov ЦыганковНоменклатура.xlsx
"""

import sys
import uuid
from pathlib import Path
from typing import List
from models import Employee, NomenclatureItem, EmployeeManager

try:
    import openpyxl
except ImportError:
    print("❌ Установите openpyxl:")
    print("   pip install openpyxl")
    sys.exit(1)


def import_nomenclature(employee_id: str, file_path: str, data_dir: str = "./data") -> dict:
    """
    Импортирует номенклатуру из XLSX файла и привязывает к сотруднику.
    
    Args:
        employee_id: ID сотрудника
        file_path: Путь к XLSX файлу
        data_dir: Директория для сохранения данных
        
    Returns:
        Словарь с результатами импорта
    """
    print(f"\n{'='*70}")
    print(f"📦 ИМПОРТ НОМЕНКЛАТУРЫ ДЛЯ СОТРУДНИКА: {employee_id}")
    print(f"{'='*70}")
    print(f"📁 Файл: {file_path}")
    
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")
    
    if not path.suffix.lower() == '.xlsx':
        raise ValueError(f"Файл должен быть .xlsx, получено: {path.suffix}")
    
    # Загружаем или создаем менеджера
    manager = EmployeeManager(data_dir)
    manager.load_all()
    
    # Получаем или создаем сотрудника
    employee = manager.get_employee(employee_id)
    if not employee:
        print(f"⚠️  Сотрудник {employee_id} не найден, создаем нового...")
        employee = manager.create_employee(
            employee_id=employee_id,
            name=employee_id  # Временно используем ID как имя
        )
    
    print(f"✅ Сотрудник: {employee.name}")
    print(f"   Уже есть номенклатуры: {len(employee.nomenclature)}")
    
    # Загружаем workbook
    print(f"\n📖 Загружаем workbook...")
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    
    # Получаем первый лист
    if not wb.sheetnames:
        raise ValueError("Файл не содержит листов")
    
    sheet_name = wb.sheetnames[0]
    print(f"📄 Лист: {sheet_name}")
    ws = wb[sheet_name]
    
    # Получаем заголовки
    headers = []
    for cell in ws[1]:
        headers.append(cell.value)
    
    print(f"📋 Найдено колонок: {len(headers)}")
    
    # Импортируем строки
    items: List[NomenclatureItem] = []
    row_number = 2
    
    print(f"\n🔄 Импортируем данные...")
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue
        
        # Создаем уникальный ID
        item_id = f"n{uuid.uuid4().hex[:8]}"
        
        # Создаем элемент номенклатуры
        item = NomenclatureItem(
            id=item_id,
            employee_id=employee_id,
            name=str(row[0] or '').strip(),
            article=str(row[1] or '').strip() if len(row) > 1 and row[1] else None,
            weight_unit=str(row[2] or '').strip() if len(row) > 2 and row[2] else None,
            weight_denominator=float(row[3]) if len(row) > 3 and row[3] is not None else None,
            weight=str(row[4] or '').strip() if len(row) > 4 and row[4] else None,
            weight_numerator=float(row[5]) if len(row) > 5 and row[5] is not None else None,
            nomenclature_type=str(row[6] or '').strip() if len(row) > 6 and row[6] else None,
            report_unit=str(row[7] or '').strip() if len(row) > 7 and row[7] else None,
            storage_unit=str(row[8] or '').strip() if len(row) > 8 and row[8] else None,
            gtin=str(row[9] or '').strip() if len(row) > 9 and row[9] else None,
            code=str(row[10] or '').strip() if len(row) > 10 and row[10] else None,
            row_number=row_number,
        )
        
        items.append(item)
        row_number += 1
    
    wb.close()
    
    print(f"✅ Прочитано строк: {len(items)}")
    
    # Валидация
    print(f"\n🔍 Валидация данных...")
    valid_items = []
    invalid_items = []
    
    for item in items:
        errors = []
        
        if not item.name or not item.name.strip():
            errors.append("Наименование обязательно")
        
        if item.weight_denominator is not None and item.weight_denominator <= 0:
            errors.append("Вес (знаменатель) должен быть > 0")
        
        if item.weight_numerator is not None and item.weight_numerator <= 0:
            errors.append("Вес (числитель) должен быть > 0")
        
        if errors:
            item.import_status = "error"
            item.error_message = "; ".join(errors)
            invalid_items.append(item)
            print(f"   ❌ Строка {item.row_number}: {item.error_message}")
        else:
            item.import_status = "success"
            valid_items.append(item)
    
    print(f"✅ Валидных: {len(valid_items)}")
    print(f"❌ Ошибок: {len(invalid_items)}")
    
    # Добавляем валидные элементы к сотруднику
    print(f"\n💾 Добавляем номенклатуру к сотруднику...")
    for item in valid_items:
        employee.add_nomenclature(item)
    
    # Сохраняем
    manager.save_all()
    
    # Показываем статистику словаря
    print(f"\n📖 Словарь для распознавания:")
    print(f"   Всего записей: {len(employee.voice_dictionary.entries)}")
    print(f"   Всего терминов: {len(employee.voice_dictionary.get_all_terms())}")
    
    print(f"✅ Сотрудник сохранен: {data_dir}/{employee_id}.json")
    
    # Статистика
    result = {
        'employee_id': employee_id,
        'employee_name': employee.name,
        'file': str(path),
        'file_size_mb': round(path.stat().st_size / 1024 / 1024, 2),
        'sheet_name': sheet_name,
        'total_rows': len(items),
        'valid_rows': len(valid_items),
        'invalid_rows': len(invalid_items),
        'total_nomenclature': len(employee.nomenclature),
        'import_time': str(path),
    }
    
    # Статистика по полям
    print(f"\n📊 Статистика по полям:")
    print(f"   Наименование: {sum(1 for i in items if i.name)} заполнено")
    print(f"   Артикул: {sum(1 for i in items if i.article)} заполнено")
    print(f"   Код: {sum(1 for i in items if i.code)} заполнено")
    print(f"   Вес (числитель): {sum(1 for i in items if i.weight_numerator is not None)} заполнено")
    print(f"   Вид номенклатуры: {sum(1 for i in items if i.nomenclature_type)} заполнено")
    
    print(f"\n{'='*70}")
    print(f"✅ ИМПОРТ ЗАВЕРШЁН")
    print(f"{'='*70}\n")
    
    return result


def main():
    """Главная функция"""
    if len(sys.argv) < 3:
        print("Использование: python import_nomenclature_v2.py <employee_id> <путь_к_файлу.xlsx>")
        print()
        print("Пример:")
        print("  python import_nomenclature_v2.py ivanov ЦыганковНоменклатура.xlsx")
        sys.exit(1)
    
    employee_id = sys.argv[1]
    file_path = sys.argv[2]
    
    try:
        result = import_nomenclature(employee_id, file_path)
        
        print(f"📦 Импортировано: {result['valid_rows']} из {result['total_rows']} записей")
        print(f"👤 Сотрудник: {result['employee_name']}")
        print(f"📋 Всего номенклатуры у сотрудника: {result['total_nomenclature']}")
        
        if result['invalid_rows'] > 0:
            print(f"⚠️  Ошибок валидации: {result['invalid_rows']}")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
