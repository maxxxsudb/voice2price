#!/usr/bin/env python3
"""
Управление словарем для распознавания речи.

Позволяет:
- Просматривать словарь сотрудника
- Добавлять варианты произношения для клиентов и номенклатуры
- Экспортировать словарь в формате SpeechKit

Использование:
    python manage_voice_dict.py <employee_id> list
    python manage_voice_dict.py <employee_id> add <original> <variant> [category]
    python manage_voice_dict.py <employee_id> export
    python manage_voice_dict.py <employee_id> speechkit
    python manage_voice_dict.py <employee_id> parse "<text>"

Примеры:
    python manage_voice_dict.py ivanov list
    python manage_voice_dict.py ivanov add "Молоко Домик" "молоко домик" nomenclature
    python manage_voice_dict.py ivanov add "ООО Ромашка" "ромашка" client
    python manage_voice_dict.py ivanov export
    python manage_voice_dict.py ivanov parse "Ромашка, молоко домик 3 упаковки"
"""

import sys
from models import EmployeeManager


def list_dictionary(employee_id: str, data_dir: str = "./data"):
    """Показать словарь сотрудника"""
    manager = EmployeeManager(data_dir)
    manager.load_all()
    
    employee = manager.get_employee(employee_id)
    if not employee:
        print(f"❌ Сотрудник {employee_id} не найден")
        return
    
    print(f"\n{'='*70}")
    print(f"📖 СЛОВАРЬ СОТРУДНИКА: {employee.name}")
    print(f"{'='*70}\n")
    
    if not employee.voice_dictionary.entries:
        print("⚠️  Словарь пуст")
        return
    
    # Группируем по категориям
    clients = [e for e in employee.voice_dictionary.entries if e.category == 'client']
    nomenclatures = [e for e in employee.voice_dictionary.entries if e.category == 'nomenclature']
    
    print(f"👥 КЛИЕНТЫ ({len(clients)} записей):")
    print("-" * 70)
    for entry in clients:
        print(f"\n  {entry.original}")
        if entry.variants:
            for variant in entry.variants:
                print(f"    → {variant}")
    
    print(f"\n\n📦 НОМЕНКЛАТУРА ({len(nomenclatures)} записей):")
    print("-" * 70)
    for entry in nomenclatures:
        print(f"\n  {entry.original}")
        if entry.variants:
            for variant in entry.variants:
                print(f"    → {variant}")
    
    print(f"\n\n📊 СТАТИСТИКА:")
    print(f"   Всего записей: {len(employee.voice_dictionary.entries)}")
    print(f"   Всего терминов: {len(employee.voice_dictionary.get_all_terms())}")
    print(f"   Клиентов: {len(clients)}")
    print(f"   Номенклатуры: {len(nomenclatures)}")


def add_variant(employee_id: str, original: str, variant: str, 
                category: str = None, data_dir: str = "./data"):
    """Добавить вариант произношения"""
    manager = EmployeeManager(data_dir)
    manager.load_all()
    
    employee = manager.get_employee(employee_id)
    if not employee:
        print(f"❌ Сотрудник {employee_id} не найден")
        return
    
    # Если категория не указана, пытаемся определить
    if category is None:
        # Ищем в существующих записях
        for entry in employee.voice_dictionary.entries:
            if entry.original == original:
                category = entry.category
                break
        
        if category is None:
            print(f"⚠️  Категория не указана и не найдена. Используйте: client или nomenclature")
            return
    
    # Добавляем вариант
    employee.add_voice_variant(original, variant, category)
    
    # Сохраняем
    manager.save_all()
    
    print(f"\n✅ Вариант добавлен:")
    print(f"   Оригинал: {original}")
    print(f"   Вариант: {variant}")
    print(f"   Категория: {category}")
    print(f"\n💾 Сохранено: {data_dir}/{employee_id}.json")


def export_dictionary(employee_id: str, data_dir: str = "./data"):
    """Экспортировать словарь"""
    manager = EmployeeManager(data_dir)
    manager.load_all()
    
    employee = manager.get_employee(employee_id)
    if not employee:
        print(f"❌ Сотрудник {employee_id} не найден")
        return
    
    print(f"\n{'='*70}")
    print(f"📖 СЛОВАРЬ ДЛЯ РАСПОЗНАВАНИЯ: {employee.name}")
    print(f"{'='*70}\n")
    
    all_terms = employee.voice_dictionary.get_all_terms()
    
    if not all_terms:
        print("⚠️  Словарь пуст")
        return
    
    print(f"Всего терминов: {len(all_terms)}\n")
    
    for term in sorted(all_terms):
        print(f"  • {term}")
    
    # Сохраняем в файл
    import json
    output_file = f"{data_dir}/{employee_id}_dictionary.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(employee.voice_dictionary.to_dict(), f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Словарь сохранен: {output_file}")


def export_speechkit_format(employee_id: str, data_dir: str = "./data"):
    """Экспортировать словарь в формате SpeechKit"""
    manager = EmployeeManager(data_dir)
    manager.load_all()
    
    employee = manager.get_employee(employee_id)
    if not employee:
        print(f"❌ Сотрудник {employee_id} не найден")
        return
    
    print(f"\n{'='*70}")
    print(f"📖 СЛОВАРЬ В ФОРМАТЕ YANDEX SPEECHKIT: {employee.name}")
    print(f"{'='*70}\n")
    
    speechkit_dict = employee.voice_dictionary.get_speechkit_format()
    
    if not speechkit_dict:
        print("⚠️  Словарь пуст или нет вариантов")
        print("\nПодсказка: добавьте варианты произношения командой:")
        print(f"  python manage_voice_dict.py {employee_id} add \"оригинал\" \"вариант\" категория")
        return
    
    print(speechkit_dict)
    
    # Сохраняем в файл
    output_file = f"{data_dir}/{employee_id}_speechkit.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(speechkit_dict)
    
    print(f"\n💾 Словарь сохранен: {output_file}")
    print(f"\n📝 Используйте этот файл для передачи в SpeechKit API")


def parse_text(employee_id: str, text: str, data_dir: str = "./data"):
    """Парсить текст заказа"""
    manager = EmployeeManager(data_dir)
    manager.load_all()
    
    employee = manager.get_employee(employee_id)
    if not employee:
        print(f"❌ Сотрудник {employee_id} не найден")
        return
    
    print(f"\n{'='*70}")
    print(f"🔍 ПАРСИНГ ТЕКСТА ЗАКАЗА")
    print(f"{'='*70}\n")
    
    print(f"Исходный текст: {text}\n")
    
    result = employee.parse_order_text(text)
    
    print(f"📊 РЕЗУЛЬТАТ ПАРСИНГА:\n")
    
    if result['clients']:
        print(f"👥 КЛИЕНТ:")
        for client in result['clients']:
            print(f"   Оригинал: {client['entry']['original']}")
            print(f"   Найдено как: {client['matched_as']}")
            print(f"   ID: {client['entry']['item_id']}")
    else:
        print(f"👥 КЛИЕНТ: не найден")
    
    print()
    
    if result['nomenclatures']:
        print(f"📦 НОМЕНКЛАТУРА:")
        for nom in result['nomenclatures']:
            print(f"   Оригинал: {nom['entry']['original']}")
            print(f"   Найдено как: {nom['matched_as']}")
            print(f"   ID: {nom['entry']['item_id']}")
    else:
        print(f"📦 НОМЕНКЛАТУРА: не найдена")
    
    print()
    
    if result['quantities']:
        print(f"🔢 КОЛИЧЕСТВА:")
        for q in result['quantities']:
            unit = q['unit'] if q['unit'] else 'шт'
            print(f"   {q['value']} {unit}")
    else:
        print(f"🔢 КОЛИЧЕСТВА: не найдены")
    
    print()
    
    if result['parsed_order']:
        print(f"✅ ЗАКАЗ СОБРАН:")
        order = result['parsed_order']
        print(f"   Клиент: {order['client_name']} (ID: {order['client_id']})")
        print(f"   Позиций: {len(order['items'])}")
        for item in order['items']:
            print(f"     • {item['nomenclature_name']} × {item['quantity']}")
    else:
        print(f"❌ ЗАКАЗ НЕ СОБРАН (не найден клиент или номенклатура)")


def main():
    """Главная функция"""
    if len(sys.argv) < 3:
        print("Использование:")
        print("  python manage_voice_dict.py <employee_id> list")
        print("  python manage_voice_dict.py <employee_id> add <original> <variant> [category]")
        print("  python manage_voice_dict.py <employee_id> export")
        print("  python manage_voice_dict.py <employee_id> speechkit")
        print("  python manage_voice_dict.py <employee_id> parse \"<text>\"")
        print()
        print("Примеры:")
        print("  python manage_voice_dict.py ivanov list")
        print('  python manage_voice_dict.py ivanov add "Молоко Домик" "молоко домик" nomenclature')
        print('  python manage_voice_dict.py ivanov add "ООО Ромашка" "ромашка" client')
        print("  python manage_voice_dict.py ivanov export")
        print('  python manage_voice_dict.py ivanov parse "Ромашка, молоко домик 3 упаковки"')
        sys.exit(1)
    
    employee_id = sys.argv[1]
    command = sys.argv[2]
    
    try:
        if command == "list":
            list_dictionary(employee_id)
        
        elif command == "add":
            if len(sys.argv) < 5:
                print("❌ Укажите original и variant")
                print('Пример: python manage_voice_dict.py ivanov add "Молоко Домик" "молоко домик" nomenclature')
                sys.exit(1)
            
            original = sys.argv[3]
            variant = sys.argv[4]
            category = sys.argv[5] if len(sys.argv) > 5 else None
            
            add_variant(employee_id, original, variant, category)
        
        elif command == "export":
            export_dictionary(employee_id)
        
        elif command == "speechkit":
            export_speechkit_format(employee_id)
        
        elif command == "parse":
            if len(sys.argv) < 4:
                print("❌ Укажите текст для парсинга")
                print('Пример: python manage_voice_dict.py ivanov parse "Ромашка, молоко домик 3 упаковки"')
                sys.exit(1)
            
            text = sys.argv[3]
            parse_text(employee_id, text)
        
        else:
            print(f"❌ Неизвестная команда: {command}")
            print("Доступные команды: list, add, export, speechkit, parse")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
