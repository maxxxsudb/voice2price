#!/usr/bin/env python3
"""
Управление голосовыми вариантами номенклатуры.

Позволяет добавлять варианты произношения для номенклатуры сотрудника,
что улучшает распознавание речи.

Использование:
    python manage_voice_variants.py <employee_id> list
    python manage_voice_variants.py <employee_id> add <item_id> <variant>
    python manage_voice_variants.py <employee_id> export
    python manage_voice_variants.py <employee_id> dictionary

Примеры:
    python manage_voice_variants.py ivanov list
    python manage_voice_variants.py ivanov add n12345678 "молоко домик"
    python manage_voice_variants.py ivanov export
    python manage_voice_variants.py ivanov dictionary
"""

import sys
import json
from models import EmployeeManager


def list_nomenclature(employee_id: str, data_dir: str = "./data"):
    """Показать список номенклатуры сотрудника"""
    manager = EmployeeManager(data_dir)
    manager.load_all()
    
    employee = manager.get_employee(employee_id)
    if not employee:
        print(f"❌ Сотрудник {employee_id} не найден")
        return
    
    print(f"\n{'='*70}")
    print(f"📋 НОМЕНКЛАТУРА СОТРУДНИКА: {employee.name}")
    print(f"{'='*70}\n")
    
    if not employee.nomenclature:
        print("⚠️  Номенклатура не найдена")
        return
    
    for idx, item in enumerate(employee.nomenclature, 1):
        if item.import_status != 'success':
            continue
        
        print(f"{idx}. [{item.id}] {item.name}")
        if item.article:
            print(f"   Артикул: {item.article}")
        if item.code:
            print(f"   Код: {item.code}")
        
        if item.voice_variants:
            print(f"   Голосовые варианты:")
            for v in item.voice_variants:
                print(f"     • {v.variant} (уверенность: {v.confidence:.2f})")
        else:
            print(f"   Голосовые варианты: нет")
        
        print()


def add_voice_variant(employee_id: str, item_id: str, variant: str, 
                      confidence: float = 1.0, data_dir: str = "./data"):
    """Добавить голосовой вариант для номенклатуры"""
    manager = EmployeeManager(data_dir)
    manager.load_all()
    
    employee = manager.get_employee(employee_id)
    if not employee:
        print(f"❌ Сотрудник {employee_id} не найден")
        return
    
    # Ищем номенклатуру по ID
    item = None
    for n in employee.nomenclature:
        if n.id == item_id:
            item = n
            break
    
    if not item:
        print(f"❌ Номенклатура {item_id} не найдена")
        print(f"\nДоступные ID:")
        for n in employee.nomenclature:
            if n.import_status == 'success':
                print(f"  {n.id}: {n.name}")
        return
    
    # Добавляем вариант
    item.add_voice_variant(variant, confidence)
    
    # Сохраняем
    manager.save_all()
    
    print(f"\n✅ Голосовой вариант добавлен:")
    print(f"   Номенклатура: {item.name}")
    print(f"   Вариант: {variant}")
    print(f"   Уверенность: {confidence:.2f}")
    print(f"\n💾 Сохранено: {data_dir}/{employee_id}.json")


def export_dictionary(employee_id: str, data_dir: str = "./data"):
    """Экспортировать словарь для распознавания"""
    manager = EmployeeManager(data_dir)
    manager.load_all()
    
    employee = manager.get_employee(employee_id)
    if not employee:
        print(f"❌ Сотрудник {employee_id} не найден")
        return
    
    print(f"\n{'='*70}")
    print(f"📖 СЛОВАРЬ ДЛЯ РАСПОЗНАВАНИЯ: {employee.name}")
    print(f"{'='*70}\n")
    
    dictionary = employee.get_voice_dictionary()
    
    if not dictionary:
        print("⚠️  Словарь пуст")
        return
    
    print(f"Всего терминов: {len(dictionary)}\n")
    
    for term, variants in dictionary.items():
        print(f"{term}:")
        for v in variants:
            print(f"  • {v}")
        print()
    
    # Сохраняем в файл
    output_file = f"{data_dir}/{employee_id}_dictionary.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dictionary, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Словарь сохранен: {output_file}")


def export_speechkit_format(employee_id: str, data_dir: str = "./data"):
    """Экспортировать словарь в формате Яндекс SpeechKit"""
    manager = EmployeeManager(data_dir)
    manager.load_all()
    
    employee = manager.get_employee(employee_id)
    if not employee:
        print(f"❌ Сотрудник {employee_id} не найден")
        return
    
    print(f"\n{'='*70}")
    print(f"📖 СЛОВАРЬ В ФОРМАТЕ YANDEX SPEECHKIT: {employee.name}")
    print(f"{'='*70}\n")
    
    speechkit_dict = employee.get_yandex_speechkit_dictionary()
    
    if not speechkit_dict:
        print("⚠️  Словарь пуст")
        return
    
    print(speechkit_dict)
    
    # Сохраняем в файл
    output_file = f"{data_dir}/{employee_id}_speechkit.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(speechkit_dict)
    
    print(f"\n💾 Словарь сохранен: {output_file}")


def main():
    """Главная функция"""
    if len(sys.argv) < 3:
        print("Использование:")
        print("  python manage_voice_variants.py <employee_id> list")
        print("  python manage_voice_variants.py <employee_id> add <item_id> <variant> [confidence]")
        print("  python manage_voice_variants.py <employee_id> export")
        print("  python manage_voice_variants.py <employee_id> dictionary")
        print()
        print("Примеры:")
        print("  python manage_voice_variants.py ivanov list")
        print('  python manage_voice_variants.py ivanov add n12345678 "молоко домик"')
        print('  python manage_voice_variants.py ivanov add n12345678 "домик в деревне" 0.9')
        print("  python manage_voice_variants.py ivanov export")
        sys.exit(1)
    
    employee_id = sys.argv[1]
    command = sys.argv[2]
    
    try:
        if command == "list":
            list_nomenclature(employee_id)
        
        elif command == "add":
            if len(sys.argv) < 5:
                print("❌ Укажите item_id и variant")
                print("Пример: python manage_voice_variants.py ivanov add n12345678 'молоко домик'")
                sys.exit(1)
            
            item_id = sys.argv[3]
            variant = sys.argv[4]
            confidence = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
            
            add_voice_variant(employee_id, item_id, variant, confidence)
        
        elif command == "export" or command == "dictionary":
            export_dictionary(employee_id)
        
        elif command == "speechkit":
            export_speechkit_format(employee_id)
        
        else:
            print(f"❌ Неизвестная команда: {command}")
            print("Доступные команды: list, add, export, dictionary, speechkit")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
