from __future__ import annotations
import json, os, time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, Optional
import paho.mqtt.client as mqtt
from exceptions import ConexionError, SuscripcionError  # استثناءات مخصصة

def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _ensure_parent(path: str):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

@dataclass
class MqttClient:
    broker: str = "mqtt.meshtastic.org"
    port: int = 1883
    username: str = "meshdev"
    password: str = "large4cats"
    client_id: str = ""
    data_store: str = "../data/data_store.json"
    debug: bool = False

    _client: mqtt.Client = field(init=False, repr=False)
    _on_json: Optional[Callable[[str, Dict], None]] = field(default=None, init=False, repr=False)
    _on_text: Optional[Callable[[str, str], None]] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.client_id or "")
        self._client.username_pw_set(self.username, self.password)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

    # -------- API --------
    def connect(self):
        if self.debug:
            print(f"[MQTT] Conectando {self.broker}:{self.port}…")
        try:
            self._client.connect(self.broker, int(self.port), 60)
        except Exception as e:
            raise ConexionError(f"Fallo conectando a {self.broker}:{self.port} → {e}") from e
        self._client.loop_start()
        time.sleep(0.5)

    def disconnect(self):
        try:
            self._client.disconnect()
        finally:
            self._client.loop_stop()

    def subscribe(self, topic: str, on_json: Optional[Callable[[str, Dict], None]] = None,
                  on_text: Optional[Callable[[str, str], None]] = None):
        self._on_json = on_json
        self._on_text = on_text
        if self.debug:
            print(f"[MQTT] Suscribiendo a {topic}")
        try:
            self._client.subscribe(topic)
        except Exception as e:
            raise SuscripcionError(f"No se pudo suscribir al tópico '{topic}': {e}") from e

    def publish_json(self, topic: str, payload: Dict):
        body = json.dumps(payload, ensure_ascii=False)
        if self.debug:
            print(f"[MQTT] Publish {topic}: {body}")
        self._client.publish(topic, body)
        self._persist({"topic": topic, "json": payload, "ts": _now_iso()})

    def publish_text(self, topic: str, text: str):
        if self.debug:
            print(f"[MQTT] Publish {topic}: {text}")
        self._client.publish(topic, text)
        self._persist({"topic": topic, "text": text, "ts": _now_iso()})

    # -------- callbacks --------
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0 and self.debug:
            print("[MQTT] Conectado")
        elif reason_code != 0:
            print(f"[MQTT] Error de conexión: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        if self.debug:
            print(f"[MQTT] Desconectado (code={reason_code})")

    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode('utf-8', errors='ignore')
        # intentar JSON
        try:
            data = json.loads(payload)
            if self._on_json:
                self._on_json(msg.topic, data)
            self._persist({"topic": msg.topic, "json": data, "ts": _now_iso()})
            if self.debug:
                print(f"[MQTT] JSON {msg.topic}: {data}")
            return
        except Exception:
            pass
        # texto
        if self._on_text:
            self._on_text(msg.topic, payload)
        self._persist({"topic": msg.topic, "text": payload, "ts": _now_iso()})
        if self.debug:
            print(f"[MQTT] TEXT {msg.topic}: {payload}")

    # -------- almacenamiento --------
    def _persist(self, record: Dict):
        try:
            _ensure_parent(self.data_store)
            items = []
            if os.path.exists(self.data_store):
                with open(self.data_store, 'r', encoding='utf-8') as f:
                    try:
                        items = json.load(f)
                    except Exception:
                        items = []
            items.append(record)
            with open(self.data_store, 'w', encoding='utf-8') as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if self.debug:
                print(f"[STORE] Error: {e}")
