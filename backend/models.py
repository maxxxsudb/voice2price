#!/usr/bin/env python3
"""
Модели данных для системы заказов.

Структура:
- Сотрудник (Employee)
  - Словарь для распознавания (Voice Dictionary)
    - Варианты названий клиентов
    - Варианты названий номенклатуры
  - Клиенты (Clients)
  - Номенклатура (Nomenclature)
  
Логика работы:
1. Менеджер говорит: "Ромашка, молоко домик, 3 упаковки"
2. SpeechKit использует словарь сотрудника для лучшего распознавания
3. Парсим текст: клиент="Ромашка", номенклатура="молоко домик", количество=3
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set
from datetime import datetime
import json
import re


@dataclass
class DictionaryEntry:
    """Запись в словаре для распознавания"""
    original: str  # Оригинальное название (из XLSX)
    variants: List[str] = field(default_factory=list)  # Варианты произношения
    category: str = "unknown"  # Категория: client, nomenclature
    item_id: Optional[str] = None  # ID связанного элемента
    
    def add_variant(self, variant: str):
        """Добавить вариант произношения"""
        if variant and variant not in self.variants:
            self.variants.append(variant)
    
    def get_all_names(self) -> List[str]:
        """Получить все варианты названий"""
        names = [self.original]
        names.extend(self.variants)
        return names
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VoiceDictionary:
    """Словарь для распознавания речи сотрудника"""
    entries: List[DictionaryEntry] = field(default_factory=list)
    
    def add_entry(self, original: str, category: str, item_id: str = None) -> DictionaryEntry:
        """Добавить запись в словарь"""
        # Проверяем что такой записи еще нет
        for entry in self.entries:
            if entry.original == original and entry.category == category:
                return entry
        
        entry = DictionaryEntry(
            original=original,
            category=category,
            item_id=item_id
        )
        self.entries.append(entry)
        return entry
    
    def add_variant(self, original: str, variant: str, category: str = None):
        """Добавить вариант произношения к существующей записи"""
        for entry in self.entries:
            if entry.original == original:
                if category is None or entry.category == category:
                    entry.add_variant(variant)
                    return
        # Если запись не найдена, создаем новую
        entry = self.add_entry(original, category or "unknown")
        entry.add_variant(variant)
    
    def get_all_terms(self) -> List[str]:
        """Получить все термины для распознавания"""
        terms = []
        for entry in self.entries:
            terms.extend(entry.get_all_names())
        return list(set(terms))  # Убираем дубликаты
    
    def get_speechkit_format(self) -> str:
        """
        Получить словарь в формате Яндекс SpeechKit.
        
        Формат:
        term1|вариант1,вариант2,вариант3
        term2|вариант1,вариант2
        """
        lines = []
        
        for entry in self.entries:
            if entry.variants:
                line = f"{entry.original}|{','.join(entry.variants)}"
                lines.append(line)
        
        return '\n'.join(lines)
    
    def find_by_text(self, text: str) -> List[Dict]:
        """Найти совпадения в тексте"""
        matches = []
        text_lower = text.lower()
        
        for entry in self.entries:
            # Проверяем все варианты
            for name in entry.get_all_names():
                if name.lower() in text_lower:
                    matches.append({
                        'entry': entry.to_dict(),
                        'matched_as': name,
                        'position': text_lower.find(name.lower())
                    })
                    break
        
        # Сортируем по позиции
        matches.sort(key=lambda x: x['position'])
        return matches
    
    def to_dict(self) -> dict:
        return {
            'entries': [e.to_dict() for e in self.entries],
            'total_entries': len(self.entries),
            'total_terms': len(self.get_all_terms())
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VoiceDictionary':
        entries = [
            DictionaryEntry(
                original=e['original'],
                variants=e.get('variants', []),
                category=e.get('category', 'unknown'),
                item_id=e.get('item_id')
            )
            for e in data.get('entries', [])
        ]
        return cls(entries=entries)


@dataclass
class NomenclatureItem:
    """Элемент номенклатуры"""
    id: str
    employee_id: str
    name: str
    article: Optional[str] = None
    code: Optional[str] = None
    weight_unit: Optional[str] = None
    weight_denominator: Optional[float] = None
    weight: Optional[str] = None
    weight_numerator: Optional[float] = None
    nomenclature_type: Optional[str] = None
    report_unit: Optional[str] = None
    storage_unit: Optional[str] = None
    gtin: Optional[str] = None
    row_number: int = 0
    import_status: str = "pending"
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Client:
    """Клиент"""
    id: str
    employee_id: str
    name: str
    code: Optional[str] = None
    business_region: Optional[str] = None
    main_manager: Optional[str] = None
    registration_date: Optional[str] = None
    client_type: Optional[str] = None
    comment: Optional[str] = None
    supplier: Optional[str] = None
    public_name: Optional[str] = None
    other_relations: Optional[str] = None
    serviced_by_sales_reps: Optional[str] = None
    carrier: Optional[str] = None
    legal_entity_type: Optional[str] = None
    driver: Optional[str] = None
    special_price_flag: Optional[str] = None
    row_number: int = 0
    import_status: str = "pending"
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OrderItem:
    """Позиция заказа"""
    nomenclature_id: str
    nomenclature_name: str
    quantity: float
    unit: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Order:
    """Заказ"""
    id: str
    employee_id: str
    client_id: str
    client_name: str
    items: List[OrderItem] = field(default_factory=list)
    raw_text: Optional[str] = None  # Исходный распознанный текст
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_item(self, nomenclature_id: str, nomenclature_name: str, quantity: float, unit: str = None):
        """Добавить позицию в заказ"""
        item = OrderItem(
            nomenclature_id=nomenclature_id,
            nomenclature_name=nomenclature_name,
            quantity=quantity,
            unit=unit
        )
        self.items.append(item)
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['items'] = [item.to_dict() for item in self.items]
        return data


@dataclass
class Employee:
    """Сотрудник"""
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    
    # Словарь для распознавания
    voice_dictionary: VoiceDictionary = field(default_factory=VoiceDictionary)
    
    # Привязанные данные
    nomenclature: List[NomenclatureItem] = field(default_factory=list)
    clients: List[Client] = field(default_factory=list)
    orders: List[Order] = field(default_factory=list)
    
    # Метаданные
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_nomenclature(self, item: NomenclatureItem):
        """Добавить номенклатуру и в словарь"""
        item.employee_id = self.id
        self.nomenclature.append(item)
        
        # Добавляем в словарь
        if item.import_status == 'success':
            entry = self.voice_dictionary.add_entry(
                original=item.name,
                category='nomenclature',
                item_id=item.id
            )
            # Добавляем артикул и код как варианты
            if item.article:
                entry.add_variant(item.article)
            if item.code:
                entry.add_variant(item.code)
    
    def add_client(self, client: Client):
        """Добавить клиента и в словарь"""
        client.employee_id = self.id
        self.clients.append(client)
        
        # Добавляем в словарь
        if client.import_status == 'success':
            entry = self.voice_dictionary.add_entry(
                original=client.name,
                category='client',
                item_id=client.id
            )
            # Добавляем код как вариант
            if client.code:
                entry.add_variant(client.code)
            # Добавляем публичное название если есть
            if client.public_name and client.public_name != client.name:
                entry.add_variant(client.public_name)
    
    def add_voice_variant(self, original: str, variant: str, category: str = None):
        """Добавить голосовой вариант"""
        self.voice_dictionary.add_variant(original, variant, category)
    
    def parse_order_text(self, text: str) -> Dict:
        """
        Парсить распознанный текст и извлекать заказ.
        
        Пример: "Ромашка, молоко домик 3 упаковки, хлеб бородинский 2 штуки"
        """
        # Находим все совпадения со словарем
        matches = self.voice_dictionary.find_by_text(text)
        
        # Разделяем на клиентов и номенклатуру
        clients = [m for m in matches if m['entry']['category'] == 'client']
        nomenclatures = [m for m in matches if m['entry']['category'] == 'nomenclature']
        
        # Извлекаем количества
        quantities = self._extract_quantities(text)
        
        return {
            'raw_text': text,
            'clients': clients,
            'nomenclatures': nomenclatures,
            'quantities': quantities,
            'parsed_order': self._build_order(clients, nomenclatures, quantities, text)
        }
    
    def _extract_quantities(self, text: str) -> List[Dict]:
        """Извлечь количества из текста"""
        quantities = []
        
        # Паттерны для чисел
        patterns = [
            r'(\d+)\s*(упаковк|штук|коробк|блок|ящик)',  # 3 упаковки
            r'(\d+)\s*(кг|г|л|мл)',  # 2 кг
            r'(\d+)',  # просто число
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                quantities.append({
                    'value': int(match.group(1)),
                    'unit': match.group(2) if len(match.groups()) > 1 else None,
                    'position': match.start(),
                    'text': match.group(0)
                })
        
        return quantities
    
    def _build_order(self, clients: List[Dict], nomenclatures: List[Dict], 
                     quantities: List[Dict], text: str) -> Optional[Dict]:
        """Собрать заказ из найденных элементов"""
        if not clients or not nomenclatures:
            return None
        
        # Берем первого клиента
        client = clients[0]
        
        # Создаем позиции заказа
        items = []
        for idx, nom in enumerate(nomenclatures):
            # Пытаемся найти количество для этой номенклатуры
            quantity = 1  # По умолчанию
            unit = None
            
            # Ищем ближайшее количество после этой номенклатуры
            nom_pos = nom['position']
            for q in quantities:
                if q['position'] > nom_pos:
                    quantity = q['value']
                    unit = q['unit']
                    break
            
            items.append({
                'nomenclature_id': nom['entry']['item_id'],
                'nomenclature_name': nom['entry']['original'],
                'matched_as': nom['matched_as'],
                'quantity': quantity,
                'unit': unit
            })
        
        return {
            'client_id': client['entry']['item_id'],
            'client_name': client['entry']['original'],
            'items': items,
            'raw_text': text
        }
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['voice_dictionary'] = self.voice_dictionary.to_dict()
        data['nomenclature'] = [n.to_dict() for n in self.nomenclature]
        data['clients'] = [c.to_dict() for c in self.clients]
        data['orders'] = [o.to_dict() for o in self.orders]
        return data
    
    def save(self, file_path: str):
        """Сохранить сотрудника в JSON файл"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, file_path: str) -> 'Employee':
        """Загрузить сотрудника из JSON файла"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        employee = cls(
            id=data['id'],
            name=data['name'],
            email=data.get('email'),
            phone=data.get('phone'),
            position=data.get('position'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
        
        # Загружаем словарь
        if 'voice_dictionary' in data:
            employee.voice_dictionary = VoiceDictionary.from_dict(data['voice_dictionary'])
        
        # Загружаем номенклатуру
        for n_data in data.get('nomenclature', []):
            item = NomenclatureItem(**{k: v for k, v in n_data.items() if k in NomenclatureItem.__dataclass_fields__})
            employee.nomenclature.append(item)
        
        # Загружаем клиентов
        for c_data in data.get('clients', []):
            client = Client(**{k: v for k, v in c_data.items() if k in Client.__dataclass_fields__})
            employee.clients.append(client)
        
        # Загружаем заказы
        for o_data in data.get('orders', []):
            order = Order(
                id=o_data['id'],
                employee_id=o_data['employee_id'],
                client_id=o_data['client_id'],
                client_name=o_data['client_name'],
                raw_text=o_data.get('raw_text'),
                created_at=o_data.get('created_at')
            )
            for item_data in o_data.get('items', []):
                order.add_item(**item_data)
            employee.orders.append(order)
        
        return employee


class EmployeeManager:
    """Менеджер для управления сотрудниками"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.employees: Dict[str, Employee] = {}
    
    def create_employee(self, employee_id: str, name: str, **kwargs) -> Employee:
        """Создать нового сотрудника"""
        if employee_id in self.employees:
            raise ValueError(f"Сотрудник с ID {employee_id} уже существует")
        
        employee = Employee(id=employee_id, name=name, **kwargs)
        self.employees[employee_id] = employee
        return employee
    
    def get_employee(self, employee_id: str) -> Optional[Employee]:
        """Получить сотрудника по ID"""
        return self.employees.get(employee_id)
    
    def list_employees(self) -> List[Employee]:
        """Получить список всех сотрудников"""
        return list(self.employees.values())
    
    def save_all(self):
        """Сохранить всех сотрудников"""
        import os
        os.makedirs(self.data_dir, exist_ok=True)
        
        for employee_id, employee in self.employees.items():
            file_path = os.path.join(self.data_dir, f"{employee_id}.json")
            employee.save(file_path)
    
    def load_all(self):
        """Загрузить всех сотрудников"""
        import os
        
        if not os.path.exists(self.data_dir):
            return
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.data_dir, filename)
                try:
                    employee = Employee.load(file_path)
                    self.employees[employee.id] = employee
                except Exception as e:
                    print(f"⚠️  Ошибка загрузки {filename}: {e}")


if __name__ == '__main__':
    # Пример использования
    manager = EmployeeManager()
    
    # Создаем сотрудника
    employee = manager.create_employee(
        employee_id="ivanov",
        name="Иванов Иван Иванович"
    )
    
    # Добавляем клиента
    client = Client(
        id="c001",
        employee_id="ivanov",
        name="ООО Ромашка",
        code="CL-001",
        public_name="Ромашка",
        import_status="success"
    )
    employee.add_client(client)
    
    # Добавляем номенклатуру
    item = NomenclatureItem(
        id="n001",
        employee_id="ivanov",
        name="Молоко Домик в деревне 3.2%",
        article="MD-001",
        import_status="success"
    )
    employee.add_nomenclature(item)
    
    # Добавляем голосовые варианты
    employee.add_voice_variant("Молоко Домик в деревне 3.2%", "молоко домик", "nomenclature")
    employee.add_voice_variant("Молоко Домик в деревне 3.2%", "домик в деревне", "nomenclature")
    employee.add_voice_variant("ООО Ромашка", "ромашка", "client")
    
    # Проверяем словарь
    print("Словарь для распознавания:")
    print(employee.voice_dictionary.get_speechkit_format())
    
    # Парсим текст заказа
    text = "Ромашка, молоко домик 3 упаковки"
    result = employee.parse_order_text(text)
    
    print(f"\nРаспознанный текст: {text}")
    print(f"Клиент: {result['clients'][0]['entry']['original'] if result['clients'] else 'не найден'}")
    print(f"Номенклатура: {result['nomenclatures'][0]['entry']['original'] if result['nomenclatures'] else 'не найдена'}")
    print(f"Количество: {result['quantities']}")
