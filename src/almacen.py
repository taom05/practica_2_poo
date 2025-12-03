from typing import Generic, TypeVar, List, Optional
T = TypeVar("T")
class Almacen(Generic[T]):
    def __init__(self):
        self._items: List[T] = []

    def agregar(self, item: T) -> None:
        self._items.append(item)

    def todos(self) -> List[T]:
        return list(self._items)

    def ultimo(self) -> Optional[T]:
        return self._items[-1] if self._items else None
