from functools import wraps
from datetime import datetime

def registrar_evento(nombre: str):
    def deco(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ts = datetime.utcnow().isoformat(timespec="seconds")
            print(f"[EVENTO {nombre}] {ts} → {func.__name__}")
            return func(*args, **kwargs)
        return wrapper
    return deco
