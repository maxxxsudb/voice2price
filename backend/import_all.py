#!/usr/bin/env python3
"""
Главный скрипт импорта данных.

Импортирует:
1. Номенклатуру из XLSX файла
2. Клиентов из XLSX файла

Использование:
    python import_all.py <файл_номенклатуры.xlsx> <файл_клиентов.xlsx>

Пример:
    python import_all.py ЦыганковНоменклатура.xlsx Клиенты.xlsx
"""

import sys
from pathlib import Path
from import_nomenclature import import_nomenclature
from import_clients import import_clients


def main():
    """Главная функция"""
    if len(sys.argv) < 3:
        print("Использование: python import_all.py <файл_номенклатуры.xlsx> <файл_клиентов.xlsx>")
        print()
        print("Пример:")
        print("  python import_all.py ЦыганковНоменклатура.xlsx Клиенты.xlsx")
        sys.exit(1)
    
    nomenclature_file = sys.argv[1]
    clients_file = sys.argv[2]
    
    print("\n" + "="*70)
    print("🚀 НАЧАЛО ИМПОРТА ДАННЫХ")
    print("="*70)
    
    # Импорт номенклатуры
    print("\n" + "="*70)
    print("📦 ЭТАП 1: ИМПОРТ НОМЕНКЛАТУРЫ")
    print("="*70)
    
    try:
        nomenclature_result = import_nomenclature(nomenclature_file)
        print(f"\n✅ Номенклатура импортирована успешно")
        print(f"   Валидных записей: {nomenclature_result['valid_rows']} из {nomenclature_result['total_rows']}")
    except Exception as e:
        print(f"\n❌ Ошибка при импорте номенклатуры: {e}")
        import traceback
        traceback.print_exc()
        nomenclature_result = None
    
    # Импорт клиентов
    print("\n" + "="*70)
    print("👥 ЭТАП 2: ИМПОРТ КЛИЕНТОВ")
    print("="*70)
    
    try:
        clients_result = import_clients(clients_file)
        print(f"\n✅ Клиенты импортированы успешно")
        print(f"   Валидных записей: {clients_result['valid_rows']} из {clients_result['total_rows']}")
    except Exception as e:
        print(f"\n❌ Ошибка при импорте клиентов: {e}")
        import traceback
        traceback.print_exc()
        clients_result = None
    
    # Итоговая статистика
    print("\n" + "="*70)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("="*70)
    
    if nomenclature_result:
        print(f"\n📦 Номенклатура:")
        print(f"   Файл: {nomenclature_result['file']}")
        print(f"   Всего записей: {nomenclature_result['total_rows']}")
        print(f"   ✅ Валидных: {nomenclature_result['valid_rows']}")
        print(f"   ❌ Ошибок: {nomenclature_result['invalid_rows']}")
        print(f"   💾 Результат: {Path(nomenclature_file).with_suffix('.import.json')}")
    
    if clients_result:
        print(f"\n👥 Клиенты:")
        print(f"   Файл: {clients_result['file']}")
        print(f"   Всего записей: {clients_result['total_rows']}")
        print(f"   ✅ Валидных: {clients_result['valid_rows']}")
        print(f"   ❌ Ошибок: {clients_result['invalid_rows']}")
        print(f"   💾 Результат: {Path(clients_file).with_suffix('.import.json')}")
    
    print("\n" + "="*70)
    print("✅ ИМПОРТ ЗАВЕРШЁН")
    print("="*70 + "\n")
    
    # Следующие шаги
    print("📋 Следующие шаги:")
    print("   1. Проверьте файлы .import.json")
    print("   2. Исправьте ошибки в исходных XLSX файлах")
    print("   3. Запустите импорт снова")
    print("   4. Загрузите данные в базу данных")
    print()


if __name__ == '__main__':
    main()
