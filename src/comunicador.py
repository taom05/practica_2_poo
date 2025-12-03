from abc import ABC, abstractmethod
from typing import Any
from .exceptions import ConexionError


class Comunicador(ABC):
    """Clase abstracta base para cualquier comunicador (MQTT, Meshtastic...)"""

    def __init__(self, nombre: str):
        self.nombre = nombre
        self.conectado = False

    @abstractmethod
    def conectar(self):
        """Conecta el comunicador"""
        pass

    @abstractmethod
    def desconectar(self):
        """Desconecta el comunicador"""
        pass

    @abstractmethod
    def enviar(self, mensaje: Any):
        """Envía un mensaje"""
        pass

    @abstractmethod
    def recibir(self) -> Any:
        """Recibe un mensaje"""
        pass

class LogMixin:
    def log(self, texto: str):
        print(f"[LOG] {texto}")


class ComunicadorConLog(Comunicador, LogMixin):
    def conectar(self):
        self.conectado = True
        self.log("Conectado correctamente")

    def desconectar(self):
        self.conectado = False
        self.log("Desconectado")

    def enviar(self, mensaje: str):
        if not self.conectado:
            raise ConexionError("No hay conexión activa para enviar mensajes")
        self.log(f"Enviando mensaje: {mensaje}")

    def recibir(self):
        if not self.conectado:
            raise ConexionError("No hay conexión activa para recibir mensajes")
        self.log("Esperando mensaje...")
        return "Mensaje recibido"
