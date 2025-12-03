from typing import Generic, TypeVar
from datetime import datetime

T = TypeVar("T")

class Mensaje(Generic[T]):
    """Clase genérica para representar un mensaje de cualquier tipo"""
    def __init__(self, contenido: T):
        self.contenido = contenido
        self.fecha = datetime.utcnow().isoformat()

    def __str__(self):
        return f"[{self.fecha}] {self.contenido}"
