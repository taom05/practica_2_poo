# exceptions.py
class AppError(Exception):
    """Error general de la aplicación."""

class ConexionError(AppError):
    """Fallo de conexión (MQTT/Meshtastic/serial)."""

class SuscripcionError(AppError):
    """Error al suscribirse a un tópico."""

class PublicacionError(AppError):
    """Error al publicar un mensaje."""

class ConfigError(AppError):
    """Configuración inválida o incompleta."""
