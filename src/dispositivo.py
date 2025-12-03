from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any


class Dispositivo:
    def __init__(self, nombre: str = "Nodo Local", protocolo: str = "mqtt"):
        self.nombre = nombre
        self.protocolo = protocolo
        self.conectado = False
        self.historial: List[Dict[str, Any]] = []
        self.posiciones: List[Dict[str, Any]] = []

    def conectar(self):
        self.conectado = True

    def desconectar(self):
        self.conectado = False

    def registrar_mensaje(self, mensaje: str, origen: str = "local", destino: str = "broadcast"):
        registro = {
            "fecha": datetime.utcnow().isoformat(),
            "mensaje": mensaje,
            "origen": origen,
            "destino": destino
        }
        self.historial.append(registro)

    def registrar_posicion(self, lat: float, lon: float, alt: float):
        registro = {
            "fecha": datetime.utcnow().isoformat(),
            "lat": lat,
            "lon": lon,
            "alt": alt
        }
        self.posiciones.append(registro)

    def guardar_datos(self, ruta: str = "../data/dispositivo.json"):
        path = Path(ruta)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "nombre": self.nombre,
            "protocolo": self.protocolo,
            "conectado": self.conectado,
            "historial": self.historial,
            "posiciones": self.posiciones
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(path)
