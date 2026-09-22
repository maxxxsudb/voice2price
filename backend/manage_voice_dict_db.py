#!/usr/bin/env python3
"""
Управление словарем для распознавания речи (PostgreSQL версия).

Использование:
    python manage_voice_dict_db.py <employee_id> list
    python manage_voice_dict_db.py <employee_id> add <original> <variant> [category]
    python manage_voice_dict_db.py <employee_id> export
    python manage_voice_dict_db.py <employee_id> speechkit
    python manage_voice_dict_db.py <employee_id> parse "<text>"
"""

import sys
from repositories import EmployeeRepository, VoiceDictionaryRepository


def list_dictionary(employee_id: str):
    """Показать словарь сотрудника"""
    employee = EmployeeRepository.get_by_id(employee_id)
    if not employee:
        print(f"❌ Сотрудник {employee_id} не найден")
        return
    
    print(f"\n{'='*70}")
    print(f"📖 СЛОВАРЬ СОТРУДНИКА: {employee.name}")
    print(f"{'='*70}\n")
    
    entries = VoiceDictionaryRepository.get_by_employee(employee_id)
    
    if not entries:
        print("⚠️  Словарь пуст")
        return
    
    # Группируем по категориям
    clients = [e for e in entries if e.category == 'client']
    nomenclatures = [e for e in entries if e.category == 'nomenclature']
    
    print(f"👥 КЛИЕНТЫ ({len(clients)} записей):")
    print("-" * 70)
    for entry in clients:
        print(f"\n  {entry.original}")
        if entry.variants:
            for variant in entry.variants:
                print(f"    → {variant.variant}")
    
    print(f"\n\n📦 НОМЕНКЛАТУРА ({len(nomenclatures)} записей):")
    print("-" * 70)
    for entry in nomenclatures:
        print(f"\n  {entry.original}")
        if entry.variants:
            for variant in entry.variants:
                print(f"    → {variant.variant}")
    
    print(f"\n\n📊 СТАТИСТИКА:")
    print(f"   Всего записей: {len(entries)}")
    
    all_terms = VoiceDictionaryRepository.get_all_terms(employee_id)
    print(f"   Всего терминов: {len(all_terms)}")
    print(f"   Клиентов: {len(clients)}")
    print(f"   Номенклатуры: {len(nomenclatures)}")


def add_variant(employee_id: str, original: str, variant: str, category: str = None):
    """Добавить вариант произношения"""
    employee = EmployeeRepository.get_by_id(employee_id)
    if not employee:
        print(f"❌ Сотрудник {employee_id} не найден")
        return
    
    # Ищем существующую запись
    entries = VoiceDictionaryRepository.get_by_employee(employee_id)
    entry = None
    
    for e in entries:
        if e.original == original:
            if category is None or e.category == category:
                entry = e
                break
    
    if not entry:
        # Создаем новую запись
        if category is None:
            print(f"⚠️  Запись не найдена. Укажите категорию: client или nomenclature")
            return
        
        entry = VoiceDictionaryRepository.create(
            employee_id=employee_id,
            original=original,
            category=category
        )
    
    # Добавляем вариант
    VoiceDictionaryRepository.add_variant(entry.id, variant)
    
    print(f"\n✅ Вариант добавлен:")
    print(f"   Оригинал: {original}")
    print(f"   Вариант: {variant}")
    print(f"   Категория: {entry.category}")


def export_dictionary(employee_id: str):
    """Экспортировать словарь"""
    employee = EmployeeRepository.get_by_id(employee_id)
    if not employee:
        print(f"❌ Сотрудник {employee_id} не найден")
        return
    
    print(f"\n{'='*70}")
    print(f"📖 СЛОВАРЬ ДЛЯ РАСПОЗНАВАНИЯ: {employee.name}")
    print(f"{'='*70}\n")
    
    all_terms = VoiceDictionaryRepository.get_all_terms(employee_id)
    
    if not all_terms:
        print("⚠️  Словарь пуст")
        return
    
    print(f"Всего терминов: {len(all_terms)}\n")
    
    for term in sorted(all_terms):
        print(f"  • {term}")


def export_speechkit_format(employee_id: str):
    """Экспортировать словарь в формате SpeechKit"""
    employee = EmployeeRepository.get_by_id(employee_id)
    if not employee:
        print(f"❌ Сотрудник {employee_id} не найден")
        return
    
    print(f"\n{'='*70}")
    print(f"📖 СЛОВАРЬ В ФОРМАТЕ YANDEX SPEECHKIT: {employee.name}")
    print(f"{'='*70}\n")
    
    speechkit_dict = VoiceDictionaryRepository.get_speechkit_format(employee_id)
    
    if not speechkit_dict:
        print("⚠️  Словарь пуст или нет вариантов")
        return
    
    print(speechkit_dict)
    
    # Сохраняем в файл
    output_file = f"{employee_id}_speechkit.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(speechkit_dict)
    
    print(f"\n💾 Словарь сохранен: {output_file}")


def main():
    """Главная функция"""
    if len(sys.argv) < 3:
        print("Использование:")
        print("  python manage_voice_dict_db.py <employee_id> list")
        print("  python manage_voice_dict_db.py <employee_id> add <original> <variant> [category]")
        print("  python manage_voice_dict_db.py <employee_id> export")
        print("  python manage_voice_dict_db.py <employee_id> speechkit")
        print()
        print("Примеры:")
        print("  python manage_voice_dict_db.py ivanov list")
        print('  python manage_voice_dict_db.py ivanov add "Молоко Домик" "молоко домик" nomenclature')
        print("  python manage_voice_dict_db.py ivanov speechkit")
        sys.exit(1)
    
    employee_id = sys.argv[1]
    command = sys.argv[2]
    
    try:
        if command == "list":
            list_dictionary(employee_id)
        
        elif command == "add":
            if len(sys.argv) < 5:
                print("❌ Укажите original и variant")
                sys.exit(1)
            
            original = sys.argv[3]
            variant = sys.argv[4]
            category = sys.argv[5] if len(sys.argv) > 5 else None
            
            add_variant(employee_id, original, variant, category)
        
        elif command == "export":
            export_dictionary(employee_id)
        
        elif command == "speechkit":
            export_speechkit_format(employee_id)
        
        else:
            print(f"❌ Неизвестная команда: {command}")
            print("Доступные команды: list, add, export, speechkit")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
