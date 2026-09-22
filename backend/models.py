#!/usr/bin/env python3
"""
Модели данных для системы импорта.

Структура:
- Сотрудник (Employee)
  - Номенклатура (Nomenclature) - привязана к сотруднику
  - Клиенты (Client) - привязаны к сотруднику
  - Словарь для распознавания (Voice Dictionary)
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime
import json


@dataclass
class VoiceVariant:
    """Вариант голосового названия номенклатуры"""
    variant: str  # Голосовой вариант (например, "арт один два три")
    original: str  # Оригинальное название
    confidence: float = 1.0  # Уверенность (0.0 - 1.0)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NomenclatureItem:
    """Элемент номенклатуры"""
    id: str  # Уникальный ID
    employee_id: str  # ID сотрудника (привязка)
    
    # Основные поля
    name: str  # Наименование
    article: Optional[str] = None  # Артикул
    code: Optional[str] = None  # Код
    
    # Вес
    weight_unit: Optional[str] = None  # Единица измерения веса
    weight_denominator: Optional[float] = None  # Вес (знаменатель)
    weight: Optional[str] = None  # Вес (текст)
    weight_numerator: Optional[float] = None  # Вес (числитель)
    
    # Категория
    nomenclature_type: Optional[str] = None  # Вид номенклатуры
    report_unit: Optional[str] = None  # Единица для отчетов
    storage_unit: Optional[str] = None  # Единица хранения
    
    # Прочее
    gtin: Optional[str] = None  # GTIN
    
    # Голосовые варианты (для распознавания)
    voice_variants: List[VoiceVariant] = field(default_factory=list)
    
    # Метаданные
    row_number: int = 0
    import_status: str = "pending"
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_voice_variant(self, variant: str, confidence: float = 1.0):
        """Добавить голосовой вариант"""
        self.voice_variants.append(VoiceVariant(
            variant=variant,
            original=self.name,
            confidence=confidence
        ))
    
    def get_all_voice_names(self) -> List[str]:
        """Получить все варианты названий для распознавания"""
        names = [self.name]
        if self.article:
            names.append(self.article)
        if self.code:
            names.append(self.code)
        names.extend([v.variant for v in self.voice_variants])
        return names
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['voice_variants'] = [v.to_dict() for v in self.voice_variants]
        return data


@dataclass
class Client:
    """Клиент"""
    id: str  # Уникальный ID
    employee_id: str  # ID сотрудника (привязка)
    
    # Основные поля
    name: str  # Наименование
    code: Optional[str] = None  # Код
    
    # Регион и менеджер
    business_region: Optional[str] = None  # Бизнес-регион
    main_manager: Optional[str] = None  # Основной менеджер
    
    # Прочее
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
    
    # Метаданные
    row_number: int = 0
    import_status: str = "pending"
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Employee:
    """Сотрудник"""
    id: str  # Уникальный ID (например, email или код)
    name: str  # Имя сотрудника
    email: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    
    # Привязанные данные
    nomenclature: List[NomenclatureItem] = field(default_factory=list)
    clients: List[Client] = field(default_factory=list)
    
    # Метаданные
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_nomenclature(self, item: NomenclatureItem):
        """Добавить номенклатуру"""
        item.employee_id = self.id
        self.nomenclature.append(item)
    
    def add_client(self, client: Client):
        """Добавить клиента"""
        client.employee_id = self.id
        self.clients.append(client)
    
    def get_voice_dictionary(self) -> Dict[str, List[str]]:
        """
        Получить словарь для распознавания речи.
        
        Returns:
            Словарь: {оригинальное_название: [варианты_произношения]}
        """
        dictionary = {}
        
        for item in self.nomenclature:
            if item.import_status == 'success':
                # Оригинальное название
                dictionary[item.name] = [item.name]
                
                # Голосовые варианты
                if item.voice_variants:
                    dictionary[item.name].extend([v.variant for v in item.voice_variants])
                
                # Артикул и код
                if item.article:
                    dictionary[item.name].append(item.article)
                if item.code:
                    dictionary[item.name].append(item.code)
        
        return dictionary
    
    def get_yandex_speechkit_dictionary(self) -> str:
        """
        Получить словарь в формате Яндекс SpeechKit.
        
        Формат:
        term1|вариант1,вариант2,вариант3
        term2|вариант1,вариант2
        """
        lines = []
        
        for item in self.nomenclature:
            if item.import_status == 'success':
                variants = []
                
                # Добавляем все варианты
                if item.article:
                    variants.append(item.article)
                if item.code:
                    variants.append(item.code)
                for v in item.voice_variants:
                    variants.append(v.variant)
                
                if variants:
                    line = f"{item.name}|{','.join(variants)}"
                    lines.append(line)
        
        return '\n'.join(lines)
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['nomenclature'] = [n.to_dict() for n in self.nomenclature]
        data['clients'] = [c.to_dict() for c in self.clients]
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
        
        # Восстанавливаем объекты
        employee = cls(
            id=data['id'],
            name=data['name'],
            email=data.get('email'),
            phone=data.get('phone'),
            position=data.get('position'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
        
        # Восстанавливаем номенклатуру
        for n_data in data.get('nomenclature', []):
            voice_variants = [
                VoiceVariant(**v) for v in n_data.get('voice_variants', [])
            ]
            item = NomenclatureItem(
                id=n_data['id'],
                employee_id=n_data['employee_id'],
                name=n_data['name'],
                article=n_data.get('article'),
                code=n_data.get('code'),
                weight_unit=n_data.get('weight_unit'),
                weight_denominator=n_data.get('weight_denominator'),
                weight=n_data.get('weight'),
                weight_numerator=n_data.get('weight_numerator'),
                nomenclature_type=n_data.get('nomenclature_type'),
                report_unit=n_data.get('report_unit'),
                storage_unit=n_data.get('storage_unit'),
                gtin=n_data.get('gtin'),
                voice_variants=voice_variants,
                row_number=n_data.get('row_number', 0),
                import_status=n_data.get('import_status', 'pending'),
                error_message=n_data.get('error_message'),
                created_at=n_data.get('created_at')
            )
            employee.nomenclature.append(item)
        
        # Восстанавливаем клиентов
        for c_data in data.get('clients', []):
            client = Client(
                id=c_data['id'],
                employee_id=c_data['employee_id'],
                name=c_data['name'],
                code=c_data.get('code'),
                business_region=c_data.get('business_region'),
                main_manager=c_data.get('main_manager'),
                registration_date=c_data.get('registration_date'),
                client_type=c_data.get('client_type'),
                comment=c_data.get('comment'),
                supplier=c_data.get('supplier'),
                public_name=c_data.get('public_name'),
                other_relations=c_data.get('other_relations'),
                serviced_by_sales_reps=c_data.get('serviced_by_sales_reps'),
                carrier=c_data.get('carrier'),
                legal_entity_type=c_data.get('legal_entity_type'),
                driver=c_data.get('driver'),
                special_price_flag=c_data.get('special_price_flag'),
                row_number=c_data.get('row_number', 0),
                import_status=c_data.get('import_status', 'pending'),
                error_message=c_data.get('error_message'),
                created_at=c_data.get('created_at')
            )
            employee.clients.append(client)
        
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
                employee = Employee.load(file_path)
                self.employees[employee.id] = employee


# Пример использования
if __name__ == '__main__':
    # Создаем менеджера
    manager = EmployeeManager()
    
    # Создаем сотрудника
    employee = manager.create_employee(
        employee_id="ivanov",
        name="Иванов Иван Иванович",
        email="ivanov@example.com",
        position="Менеджер"
    )
    
    # Добавляем номенклатуру
    item1 = NomenclatureItem(
        id="n001",
        employee_id="ivanov",
        name="Молоко Домик в деревне 3.2%",
        article="MD-001",
        code="12345"
    )
    item1.add_voice_variant("молоко домик", 0.95)
    item1.add_voice_variant("домик в деревне", 0.90)
    item1.add_voice_variant("эм дэ ноль один", 0.85)
    
    employee.add_nomenclature(item1)
    
    # Добавляем клиента
    client1 = Client(
        id="c001",
        employee_id="ivanov",
        name="ООО Ромашка",
        code="CL-001",
        business_region="Москва"
    )
    employee.add_client(client1)
    
    # Получаем словарь для распознавания
    print("Словарь для распознавания:")
    dictionary = employee.get_voice_dictionary()
    for term, variants in dictionary.items():
        print(f"  {term}: {variants}")
    
    print("\nСловарь в формате SpeechKit:")
    print(employee.get_yandex_speechkit_dictionary())
    
    # Сохраняем
    manager.save_all()
    print(f"\n✅ Сотрудник сохранен: {employee.id}.json")
