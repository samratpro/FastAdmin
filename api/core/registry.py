from typing import Dict, Type, Any
from common.orm import Model

# The ModelRegistry stores metadata about models that should be exposed in the Admin panel.
# Key: Model class name (e.g., "Post")
# Value: Dict containing the model class and admin configuration.
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {}

def register_admin(
    app_name: str,
    display_name: str,
    list_display: list[str] = None,
    search_fields: list[str] = None,
    filter_fields: list[str] = None,
    exclude_fields: list[str] = None,
    icon: str = "",
):
    """Decorator to register a model for the admin panel."""
    def wrapper(cls):
        MODEL_REGISTRY[cls.__name__] = {
            "model": cls,
            "app_name": app_name,
            "display_name": display_name,
            "list_display": list_display or ["id"],
            "search_fields": search_fields or [],
            "filter_fields": filter_fields,
            "exclude_fields": exclude_fields or [],
            "icon": icon,
        }
        return cls
    return wrapper

def get_model_by_name(name: str) -> Type[Model]:
    """Returns the model class for a given name."""
    meta = MODEL_REGISTRY.get(name)
    if not meta:
        return None
    return meta["model"]

def get_all_admin_models() -> Dict[str, Any]:
    """Returns all models registered for the admin panel."""
    return MODEL_REGISTRY
