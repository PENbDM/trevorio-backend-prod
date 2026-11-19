from decimal import Decimal
from datetime import datetime


def custom_serializer(obj):
    if isinstance(obj, Decimal):
        return str(obj)

    elif isinstance(obj, datetime):
        return obj.isoformat()

    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")



