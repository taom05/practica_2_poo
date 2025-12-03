from __future__ import annotations
import base64
import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import paho.mqtt.client as mqtt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from meshtastic.protobuf import mesh_pb2, mqtt_pb2, portnums_pb2
from meshtastic import BROADCAST_NUM, protocols


# ---------------- utilidades internas ----------------

def _xor_hash(data: bytes) -> int:
    x = 0
    for b in data:
        x ^= b
    return x


def _topic_hash(name: str, key_b64: str) -> int:
    kb = key_b64.replace('-', '+').replace('_', '/')
    key_bytes = base64.b64decode(kb.encode('utf-8'))
    return _xor_hash(name.encode('utf-8')) ^ _xor_hash(key_bytes)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _ensure_parent(path: str):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


# ---------------- clase principal ----------------

@dataclass
class MeshtasticGateway:
    # Conexión MQTT
    broker: str = "mqtt.meshtastic.org"
    port: int = 1883
    username: str = "meshdev"
    password: str = "large4cats"

    # Ruta Meshtastic
    root_topic: str = "msh/EU_868/ES/2/e/"
    channel: str = "TestMQTT"
    key_b64: str = "ymACgCy9Tdb8jHbLxUxZ/4ADX+BWLOGVihmKHcHTVyo="

    # Identidad local
    node_name: str = "!abcdeff1"   # ← رقمك؛ غيّره إن لزم
    client_short: str = "CLI"
    client_long: str = "ClienteCLI"
    hw_model: int = 255

    # Varios
    debug: bool = False
    persist_path: str = "../data/data_store.json"  # JSONL (una línea por registro)

    # Internos
    _client: mqtt.Client = field(init=False, repr=False)
    _subscribe_topic: str = field(default="", init=False, repr=False)
    _publish_topic: str = field(default="", init=False, repr=False)
    _node_number: int = field(default=0, init=False, repr=False)
    _msg_id: int = field(default_factory=lambda: random.getrandbits(32), init=False, repr=False)

    # Callback de texto descodificado (opcional, settable desde fuera)
    on_text: Optional[Callable[[str, str], None]] = field(default=None, repr=False)

    # --------------- ciclo de vida ---------------

    def __post_init__(self):
        # Cliente MQTT
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="")
        self._client.username_pw_set(self.username, self.password)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        # Normalizar clave
        self.key_b64 = self._normalize_key(self.key_b64)

        # Número de nodo derivado del nombre fijo
        self._node_number = int(self.node_name[1:], 16)

        # Preparar carpeta de persistencia
        try:
            _ensure_parent(self._abs_persist_path())
        except Exception:
            pass

    def connect(self):
        if self.debug:
            print(f"[GW] Conectando {self.broker}:{self.port}…")
        self._client.connect(self.broker, int(self.port), 60)
        self._client.loop_start()
        time.sleep(0.6)

    def disconnect(self):
        try:
            self._client.disconnect()
        finally:
            self._client.loop_stop()

    # --------------- API pública ---------------

    def send_text(self, text: str, destination: Optional[str] = None):
        """Enviar texto (broadcast si destination es None)."""
        d = mesh_pb2.Data()
        d.portnum = portnums_pb2.TEXT_MESSAGE_APP
        d.payload = text.encode('utf-8')

        dest_id = BROADCAST_NUM if not destination else int(destination[1:], 16)
        se = self._make_envelope(dest_id, d)

        self._client.publish(self._publish_topic, se.SerializeToString())

        # Persistencia (saliente)
        self._persist({
            "ts": _now_iso(),
            "proto": "meshtastic",
            "dir": "out",
            "type": "text",
            "channel": self.channel,
            "destination": destination or "broadcast",
            "text": text
        })

        if self.debug:
            print(f"[GW] Enviado texto → {destination or 'broadcast'}: {text}")

    def send_nodeinfo(self, want_response: bool = False):
        """Enviar NodeInfo (identidad del nodo)."""
        u = mesh_pb2.User()
        setattr(u, "id", self.node_name)
        setattr(u, "long_name", self.client_long)
        setattr(u, "short_name", self.client_short)
        setattr(u, "hw_model", self.hw_model)

        d = mesh_pb2.Data()
        d.portnum = portnums_pb2.NODEINFO_APP
        d.payload = u.SerializeToString()
        d.want_response = want_response

        se = self._make_envelope(BROADCAST_NUM, d)
        self._client.publish(self._publish_topic, se.SerializeToString())

        self._persist({
            "ts": _now_iso(),
            "proto": "meshtastic",
            "dir": "out",
            "type": "nodeinfo",
            "channel": self.channel,
            "gateway_id": self.node_name
        })

        if self.debug:
            print(f"[GW] NodeInfo enviado")

    def send_position(self, lat: float, lon: float, alt: float):
        """Enviar posición (lat/lon en grados, alt en metros)."""
        p = mesh_pb2.Position()
        p.latitude_i = int(lat * 1e7)
        p.longitude_i = int(lon * 1e7)
        p.altitude = int(alt)
        p.time = int(time.time())

        d = mesh_pb2.Data()
        d.portnum = portnums_pb2.POSITION_APP
        d.payload = p.SerializeToString()
        d.want_response = True

        se = self._make_envelope(BROADCAST_NUM, d)
        self._client.publish(self._publish_topic, se.SerializeToString())

        self._persist({
            "ts": _now_iso(),
            "proto": "meshtastic",
            "dir": "out",
            "type": "position",
            "channel": self.channel,
            "lat": lat,
            "lon": lon,
            "alt": alt
        })

        if self.debug:
            print(f"[GW] Posición enviada lat={lat}, lon={lon}, alt={alt}")

    # --------------- callbacks MQTT ---------------

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        self._set_topics()
        if reason_code == 0:
            if self.debug:
                print("[GW] Conectado. Suscribiendo…")
            client.subscribe(self._subscribe_topic)
        else:
            print(f"[GW] Error de conexión: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        if self.debug:
            print(f"[GW] Desconectado (code={reason_code})")

    def _on_message(self, client, userdata, msg):
        """Procesa ServiceEnvelope → MeshPacket; descifra si es necesario; intenta decodificar el payload."""
        se = mqtt_pb2.ServiceEnvelope()
        try:
            se.ParseFromString(msg.payload)
            mp = se.packet
        except Exception:
            if self.debug:
                print(f"[GW] No es ServiceEnvelope en {msg.topic}")
            return

        # Descifrar si viene cifrado
        if mp.HasField("encrypted") and not mp.HasField("decoded"):
            self._decrypt(mp)

        port_num = mp.decoded.portnum if mp.HasField("decoded") else None
        handler = protocols.get(port_num) if port_num is not None else None

        texto: Optional[str] = None
        if handler and handler.protobufFactory and mp.HasField("decoded"):
            try:
                pb = handler.protobufFactory()
                pb.ParseFromString(mp.decoded.payload)
                texto = str(pb).replace('\n', ' ').replace('\r', ' ').strip()
            except Exception:
                texto = None

        if texto is None and mp.HasField("decoded"):
            # Intento de texto plano
            try:
                texto = mp.decoded.payload.decode('utf-8', errors='ignore')
            except Exception:
                texto = None

        # Log amigable
        if self.debug:
            print(f"[GW][{port_num}] {texto if texto is not None else '<payload binario>'}")

        # Callback del usuario
        if self.on_text and texto is not None:
            try:
                self.on_text(se.gateway_id or "unknown", texto)
            except Exception:
                pass

        # Persistencia (entrante)
        self._persist({
            "ts": _now_iso(),
            "proto": "meshtastic",
            "dir": "in",
            "type": "decoded" if mp.HasField("decoded") else "encrypted",
            "channel": se.channel_id or self.channel,
            "gateway_id": se.gateway_id or "",
            "topic": msg.topic,
            "portnum": int(port_num) if port_num is not None else None,
            "text": texto
        })

    # --------------- cifrado/descifrado ---------------

    def _decrypt(self, mp: mesh_pb2.MeshPacket):
        try:
            key_bytes = base64.b64decode(self.key_b64.encode('ascii'))
            nonce = mp.id.to_bytes(8, "little") + getattr(mp, "from").to_bytes(8, "little")
            cipher = Cipher(algorithms.AES(key_bytes), modes.CTR(nonce), backend=default_backend())
            dec = cipher.decryptor()
            decrypted = dec.update(getattr(mp, "encrypted")) + dec.finalize()
            data = mesh_pb2.Data()
            data.ParseFromString(decrypted)
            mp.decoded.CopyFrom(data)
        except Exception as e:
            if self.debug:
                print(f"[GW] Error de descifrado: {e}")

    def _encrypt(self, data: mesh_pb2.Data, mp: mesh_pb2.MeshPacket) -> bytes:
        key_bytes = base64.b64decode(self.key_b64.encode('ascii'))
        nonce = mp.id.to_bytes(8, "little") + self._node_number.to_bytes(8, "little")
        cipher = Cipher(algorithms.AES(key_bytes), modes.CTR(nonce), backend=default_backend())
        enc = cipher.encryptor()
        return enc.update(data.SerializeToString()) + enc.finalize()

    def _make_envelope(self, destination_id: int, data: mesh_pb2.Data) -> mqtt_pb2.ServiceEnvelope:
        mp = mesh_pb2.MeshPacket()
        mp.id = self._msg_id
        self._msg_id += 1

        setattr(mp, "from", self._node_number)
        mp.to = destination_id
        mp.want_ack = False
        mp.channel = _topic_hash(self.channel, self.key_b64)
        mp.hop_limit = 3

        # cifrado (siempre que haya key)
        mp.encrypted = self._encrypt(data, mp)

        se = mqtt_pb2.ServiceEnvelope()
        se.packet.CopyFrom(mp)
        se.channel_id = self.channel
        se.gateway_id = self.node_name
        return se

    # --------------- helpers internos ---------------

    def _normalize_key(self, key_b64: str) -> str:
        if key_b64 == "AQ==":
            # valor educativo → expandir a 128 bits
            key_b64 = "1PG7OiApB1nwvP+rz05pAQ=="
        padded = key_b64.ljust(len(key_b64) + ((4 - (len(key_b64) % 4)) % 4), '=')
        return padded.replace('-', '+').replace('_', '/')

    def _set_topics(self):
        root = self.root_topic.rstrip('/') + '/'
        self._subscribe_topic = f"{root}{self.channel}/#"
        self._publish_topic = f"{root}{self.channel}/{self.node_name}"
        if self.debug:
            print(f"[GW] sub={self._subscribe_topic} | pub={self._publish_topic}")

    def _abs_persist_path(self) -> str:
        # almacenar en ../data/data_store.json relativo a este archivo
        base = os.path.join(os.path.dirname(__file__), self.persist_path)
        return os.path.normpath(base)

    def _persist(self, record: dict):
        """Guarda en JSONL (una línea por registro) para no bloquear por tamaño."""
        try:
            path = self._abs_persist_path()
            _ensure_parent(path)
            # Guardamos como JSON por línea (más robusto si hay concurrencia ligera)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            if self.debug:
                print(f"[STORE] Error al persistir: {e}")
