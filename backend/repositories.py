"""
Репозитории для работы с базой данных.
"""

from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from models_db import Employee, Nomenclature, Client, VoiceDictionary, VoiceVariant, Order, OrderItem
from database import get_session, close_session, DictionaryCache
import uuid


class EmployeeRepository:
    """Репозиторий для работы с сотрудниками"""
    
    @staticmethod
    def create(employee_id: str, name: str, email: str = None, phone: str = None, position: str = None) -> Employee:
        """Создать сотрудника"""
        session = get_session()
        try:
            employee = Employee(
                id=employee_id,
                name=name,
                email=email,
                phone=phone,
                position=position
            )
            session.add(employee)
            session.commit()
            session.refresh(employee)
            return employee
        finally:
            close_session()
    
    @staticmethod
    def get_by_id(employee_id: str) -> Optional[Employee]:
        """Получить сотрудника по ID"""
        session = get_session()
        try:
            return session.query(Employee).filter(Employee.id == employee_id).first()
        finally:
            close_session()
    
    @staticmethod
    def get_all() -> List[Employee]:
        """Получить всех сотрудников"""
        session = get_session()
        try:
            return session.query(Employee).all()
        finally:
            close_session()
    
    @staticmethod
    def update(employee_id: str, **kwargs) -> Optional[Employee]:
        """Обновить сотрудника"""
        session = get_session()
        try:
            employee = session.query(Employee).filter(Employee.id == employee_id).first()
            if employee:
                for key, value in kwargs.items():
                    if hasattr(employee, key):
                        setattr(employee, key, value)
                session.commit()
                session.refresh(employee)
            return employee
        finally:
            close_session()
    
    @staticmethod
    def delete(employee_id: str) -> bool:
        """Удалить сотрудника"""
        session = get_session()
        try:
            employee = session.query(Employee).filter(Employee.id == employee_id).first()
            if employee:
                session.delete(employee)
                session.commit()
                return True
            return False
        finally:
            close_session()


class NomenclatureRepository:
    """Репозиторий для работы с номенклатурой"""
    
    @staticmethod
    def create(data: dict) -> Nomenclature:
        """Создать элемент номенклатуры"""
        session = get_session()
        try:
            if 'id' not in data:
                data['id'] = f"n{uuid.uuid4().hex[:8]}"
            
            nomenclature = Nomenclature(**data)
            session.add(nomenclature)
            session.commit()
            session.refresh(nomenclature)
            return nomenclature
        finally:
            close_session()
    
    @staticmethod
    def get_by_id(nomenclature_id: str) -> Optional[Nomenclature]:
        """Получить номенклатуру по ID"""
        session = get_session()
        try:
            return session.query(Nomenclature).filter(Nomenclature.id == nomenclature_id).first()
        finally:
            close_session()
    
    @staticmethod
    def get_by_employee(employee_id: str) -> List[Nomenclature]:
        """Получить номенклатуру сотрудника"""
        session = get_session()
        try:
            return session.query(Nomenclature).filter(
                Nomenclature.employee_id == employee_id,
                Nomenclature.import_status == 'success'
            ).all()
        finally:
            close_session()
    
    @staticmethod
    def bulk_create(items: List[dict]) -> List[Nomenclature]:
        """Массовое создание номенклатуры"""
        session = get_session()
        try:
            nomenclatures = []
            for data in items:
                if 'id' not in data:
                    data['id'] = f"n{uuid.uuid4().hex[:8]}"
                nomenclature = Nomenclature(**data)
                session.add(nomenclature)
                nomenclatures.append(nomenclature)
            
            session.commit()
            for n in nomenclatures:
                session.refresh(n)
            return nomenclatures
        finally:
            close_session()


class ClientRepository:
    """Репозиторий для работы с клиентами"""
    
    @staticmethod
    def create(data: dict) -> Client:
        """Создать клиента"""
        session = get_session()
        try:
            if 'id' not in data:
                data['id'] = f"c{uuid.uuid4().hex[:8]}"
            
            client = Client(**data)
            session.add(client)
            session.commit()
            session.refresh(client)
            return client
        finally:
            close_session()
    
    @staticmethod
    def get_by_id(client_id: str) -> Optional[Client]:
        """Получить клиента по ID"""
        session = get_session()
        try:
            return session.query(Client).filter(Client.id == client_id).first()
        finally:
            close_session()
    
    @staticmethod
    def get_by_employee(employee_id: str) -> List[Client]:
        """Получить клиентов сотрудника"""
        session = get_session()
        try:
            return session.query(Client).filter(
                Client.employee_id == employee_id,
                Client.import_status == 'success'
            ).all()
        finally:
            close_session()
    
    @staticmethod
    def bulk_create(clients: List[dict]) -> List[Client]:
        """Массовое создание клиентов"""
        session = get_session()
        try:
            created_clients = []
            for data in clients:
                if 'id' not in data:
                    data['id'] = f"c{uuid.uuid4().hex[:8]}"
                client = Client(**data)
                session.add(client)
                created_clients.append(client)
            
            session.commit()
            for c in created_clients:
                session.refresh(c)
            return created_clients
        finally:
            close_session()


class VoiceDictionaryRepository:
    """Репозиторий для работы со словарем"""
    
    @staticmethod
    def get_by_employee(employee_id: str) -> List[VoiceDictionary]:
        """Получить словарь сотрудника"""
        # Сначала проверяем кэш
        cached = DictionaryCache.get(employee_id)
        if cached:
            return cached
        
        session = get_session()
        try:
            entries = session.query(VoiceDictionary).filter(
                VoiceDictionary.employee_id == employee_id
            ).all()
            
            # Сохраняем в кэш
            DictionaryCache.set(employee_id, [e.to_dict() for e in entries])
            
            return entries
        finally:
            close_session()
    
    @staticmethod
    def create(employee_id: str, original: str, category: str, item_id: str = None) -> VoiceDictionary:
        """Создать запись в словаре"""
        session = get_session()
        try:
            # Проверяем что такая запись еще не существует
            existing = session.query(VoiceDictionary).filter(
                VoiceDictionary.employee_id == employee_id,
                VoiceDictionary.original == original,
                VoiceDictionary.category == category
            ).first()
            
            if existing:
                return existing
            
            entry = VoiceDictionary(
                employee_id=employee_id,
                original=original,
                category=category,
                item_id=item_id
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            
            # Инвалидируем кэш
            DictionaryCache.invalidate(employee_id)
            
            return entry
        finally:
            close_session()
    
    @staticmethod
    def get_by_original_and_category(employee_id: str, original: str, category: str) -> Optional[VoiceDictionary]:
        """Получить запись словаря по оригинальному названию и категории"""
        session = get_session()
        try:
            return session.query(VoiceDictionary).filter(
                VoiceDictionary.employee_id == employee_id,
                VoiceDictionary.original == original,
                VoiceDictionary.category == category
            ).first()
        finally:
            close_session()
    
    @staticmethod
    def add_variant(dictionary_id: int, variant: str, confidence: float = 1.0) -> VoiceVariant:
        """Добавить вариант произношения"""
        session = get_session()
        try:
            # Проверяем что вариант еще не добавлен
            existing = session.query(VoiceVariant).filter(
                VoiceVariant.dictionary_id == dictionary_id,
                VoiceVariant.variant == variant
            ).first()
            
            if existing:
                return existing
            
            voice_variant = VoiceVariant(
                dictionary_id=dictionary_id,
                variant=variant,
                confidence=confidence
            )
            session.add(voice_variant)
            session.commit()
            session.refresh(voice_variant)
            
            # Инвалидируем кэш
            entry = session.query(VoiceDictionary).filter(VoiceDictionary.id == dictionary_id).first()
            if entry:
                DictionaryCache.invalidate(entry.employee_id)
            
            return voice_variant
        finally:
            close_session()
    
    @staticmethod
    def get_all_terms(employee_id: str) -> List[str]:
        """Получить все термины для распознавания"""
        entries = VoiceDictionaryRepository.get_by_employee(employee_id)
        terms = []
        
        for entry in entries:
            terms.append(entry.original)
            for variant in entry.variants:
                terms.append(variant.variant)
        
        return list(set(terms))
    
    @staticmethod
    def get_speechkit_format(employee_id: str) -> str:
        """Получить словарь в формате SpeechKit"""
        entries = VoiceDictionaryRepository.get_by_employee(employee_id)
        lines = []
        
        for entry in entries:
            if entry.variants:
                variants_str = ','.join([v.variant for v in entry.variants])
                lines.append(f"{entry.original}|{variants_str}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def delete_variant(variant_id: int) -> bool:
        """Удалить вариант произношения"""
        session = get_session()
        try:
            variant = session.query(VoiceVariant).filter(VoiceVariant.id == variant_id).first()
            if variant:
                # Получаем employee_id для инвалидации кэша
                entry = session.query(VoiceDictionary).filter(VoiceDictionary.id == variant.dictionary_id).first()
                employee_id = entry.employee_id if entry else None
                
                session.delete(variant)
                session.commit()
                
                # Инвалидируем кэш
                if employee_id:
                    DictionaryCache.invalidate(employee_id)
                
                return True
            return False
        finally:
            close_session()


class OrderRepository:
    """Репозиторий для работы с заказами"""
    
    @staticmethod
    def create(data: dict) -> Order:
        """Создать заказ"""
        session = get_session()
        try:
            if 'id' not in data:
                data['id'] = f"o{uuid.uuid4().hex[:8]}"
            
            order = Order(**data)
            session.add(order)
            session.commit()
            session.refresh(order)
            return order
        finally:
            close_session()
    
    @staticmethod
    def add_item(order_id: str, nomenclature_id: str, nomenclature_name: str, 
                 quantity: float, unit: str = None) -> OrderItem:
        """Добавить позицию в заказ"""
        session = get_session()
        try:
            item = OrderItem(
                order_id=order_id,
                nomenclature_id=nomenclature_id,
                nomenclature_name=nomenclature_name,
                quantity=quantity,
                unit=unit
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return item
        finally:
            close_session()
    
    @staticmethod
    def get_by_employee(employee_id: str) -> List[Order]:
        """Получить заказы сотрудника"""
        session = get_session()
        try:
            return session.query(Order).filter(
                Order.employee_id == employee_id
            ).order_by(Order.created_at.desc()).all()
        finally:
            close_session()


class UnitOfMeasureRepository:
    """Репозиторий для работы с единицами измерения"""
    
    @staticmethod
    def create(data: dict) -> 'UnitOfMeasure':
        """Создать единицу измерения"""
        from models_db import UnitOfMeasure
        session = get_session()
        try:
            if 'id' not in data:
                data['id'] = f"u{uuid.uuid4().hex[:8]}"
            
            unit = UnitOfMeasure(**data)
            session.add(unit)
            session.commit()
            session.refresh(unit)
            return unit
        finally:
            close_session()
    
    @staticmethod
    def get_by_employee(employee_id: str) -> List['UnitOfMeasure']:
        """Получить единицы измерения сотрудника"""
        from models_db import UnitOfMeasure
        session = get_session()
        try:
            return session.query(UnitOfMeasure).filter(
                UnitOfMeasure.employee_id == employee_id
            ).all()
        finally:
            close_session()
    
    @staticmethod
    def add_variant(unit_id: str, variant: str, confidence: float = 1.0) -> 'UnitVariant':
        """Добавить вариант произношения единицы измерения"""
        from models_db import UnitVariant
        session = get_session()
        try:
            # Проверяем что вариант еще не добавлен
            existing = session.query(UnitVariant).filter(
                UnitVariant.unit_id == unit_id,
                UnitVariant.variant == variant
            ).first()
            
            if existing:
                return existing
            
            unit_variant = UnitVariant(
                unit_id=unit_id,
                variant=variant,
                confidence=confidence
            )
            session.add(unit_variant)
            session.commit()
            session.refresh(unit_variant)
            return unit_variant
        finally:
            close_session()
    
    @staticmethod
    def delete_variant(variant_id: int) -> bool:
        """Удалить вариант произношения единицы измерения"""
        from models_db import UnitVariant
        session = get_session()
        try:
            variant = session.query(UnitVariant).filter(UnitVariant.id == variant_id).first()
            if variant:
                session.delete(variant)
                session.commit()
                return True
            return False
        finally:
            close_session()


if __name__ == '__main__':
    print("Тестирование репозиториев...")
    
    # Создаем тестового сотрудника
    emp = EmployeeRepository.create("test_emp", "Test Employee")
    print(f"✅ Создан сотрудник: {emp.id}")
    
    # Получаем сотрудника
    emp = EmployeeRepository.get_by_id("test_emp")
    print(f"✅ Получен сотрудник: {emp.name}")
    
    # Создаем номенклатуру
    nom = NomenclatureRepository.create({
        'employee_id': 'test_emp',
        'name': 'Test Product',
        'article': 'TP-001',
        'import_status': 'success'
    })
    print(f"✅ Создана номенклатура: {nom.name}")
    
    # Создаем запись в словаре
    dict_entry = VoiceDictionaryRepository.create(
        employee_id='test_emp',
        original='Test Product',
        category='nomenclature',
        item_id=nom.id
    )
    print(f"✅ Создана запись в словаре: {dict_entry.original}")
    
    # Добавляем вариант
    variant = VoiceDictionaryRepository.add_variant(
        dictionary_id=dict_entry.id,
        variant='тест продукт'
    )
    print(f"✅ Добавлен вариант: {variant.variant}")
    
    # Получаем все термины
    terms = VoiceDictionaryRepository.get_all_terms('test_emp')
    print(f"✅ Все термины: {terms}")
    
    # Получаем формат SpeechKit
    speechkit = VoiceDictionaryRepository.get_speechkit_format('test_emp')
    print(f"✅ SpeechKit формат:\n{speechkit}")
    
    # Удаляем тестовые данные
    EmployeeRepository.delete('test_emp')
    print("✅ Тестовые данные удалены")
