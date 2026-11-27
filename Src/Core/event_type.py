from enum import Enum


class EventType(Enum):
    """Типы событий, распространяемых через шаблон «Наблюдатель».

    Единое перечисление позволяет подписчикам фильтровать интересующие события без строковых литералов.
    """

    # Создана доменная сущность
    ENTITY_CREATED = "entity_created"
    # Изменена доменная сущность
    ENTITY_UPDATED = "entity_updated"
    # Удалена доменная сущность
    ENTITY_DELETED = "entity_deleted"
    # Проведена складская операция в журнале
    TRANSACTION_ADDED = "transaction_added"
    # Выполнен HTTP-запрос к Web API
    WEB_REQUEST = "web_request"
    # Ошибка при обработке HTTP-запроса
    WEB_ERROR = "web_error"
    # Загружены настройки приложения
    SETTINGS_LOADED = "settings_loaded"
    # Изменены параметры настроек приложения
    SETTINGS_CHANGED = "settings_changed"
