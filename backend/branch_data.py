"""Everything the order parser needs about one branch, as plain dicts."""


def load_catalog(employee_id):
    from repositories import NomenclatureRepository
    return [
        {'id': item.id, 'name': item.name, 'article': item.article,
         'code': item.code, 'storage_unit': item.storage_unit,
         'report_unit': item.report_unit,
         'nomenclature_type': getattr(item, 'nomenclature_type', None),
         'max_quantity': getattr(item, 'max_quantity', None)}
        for item in NomenclatureRepository.get_by_employee(employee_id)
    ]


def load_clients(employee_id):
    from repositories import ClientRepository
    return [{'id': c.id, 'name': c.name, 'code': c.code, 'public_name': c.public_name}
            for c in ClientRepository.get_by_employee(employee_id)]


def load_dictionary(employee_id):
    from repositories import VoiceDictionaryRepository
    return VoiceDictionaryRepository.get_data(employee_id)


def load_branch(employee_id):
    """Catalog, clients, pronunciation dictionary and parsing options of a branch."""
    from order_settings import clean
    from repositories import EmployeeRepository
    employee = EmployeeRepository.get_by_id(employee_id)
    if not employee:
        raise ValueError('Выбранный филиал не найден')
    return {
        'catalog': load_catalog(employee_id),
        'clients': load_clients(employee_id),
        'dictionary': load_dictionary(employee_id),
        'settings': clean(employee.get_order_settings()),
    }


def validation(employee_id):
    from catalog_validation import validate_catalog
    from repositories import EmployeeRepository
    employee = EmployeeRepository.get_by_id(employee_id)
    return validate_catalog(load_catalog(employee_id), load_dictionary(employee_id),
                            load_clients(employee_id), employee.get_order_settings() if employee else None)
