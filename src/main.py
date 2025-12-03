from __future__ import annotations
import argparse
import json
import os
from typing import Any, Dict, Optional
from meshtastic_client import MeshtasticGateway


# ========= CARGA CONFIG =========
def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    cfg = {
        "mqtt": {
            "broker": "",
            "port": 1883,
        },
        "meshtastic": {
             "broker": "mqtt.meshtastic.org",
            "port": 1883,
            "username": "meshdev",
            "password": "large4cats",
            "root_topic": "msh/EU_868/ES/2/e/",
            "channel": "TestMQTT",
            "key": "ymACgCy9Tdb8jHbLxUxZ/4ADX+BWLOGVihmKHcHTVyo="
        },
        "almacen": {
            "archivo": "../data/data_store.json"
        }
    }
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user = json.load(f)
            for k in ("mqtt", "meshtastic", "almacen"):
                if k in user and isinstance(user[k], dict):
                    cfg[k].update(user[k])
        except Exception:
            pass
    return cfg


# ========= ENVÍO / ESCUCHA =========
def send_meshtastic(cfg: Dict[str, Any], canal: str, mensaje: str):
    m = cfg["mqtt"]
    t = cfg["meshtastic"]

    prtin=("t")
    gw = MeshtasticGateway(
        broker="mqtt.meshtastic.org", #t["broker"],
        port=t["port"],
        username=t["username"],
        password=t["password"],
        root_topic=t["root_topic"],
        channel=t["channel"],
        key_b64=t["key"],
        debug=True
    )
    gw.connect()
    gw.send_text(mensaje)
    gw.disconnect()
    print(f"Enviado en canal '{canal}': {mensaje}")


def listen_meshtastic(cfg: Dict[str, Any], canal: str):
    m = cfg["mqtt"]; t = cfg["meshtastic"]

    print(t)
    gw = MeshtasticGateway(
        broker=m["broker"],
        port=m["port"],
        username=m["username"],
        password=m["password"],
        root_topic=t["root_topic"],
        channel=canal,
        key_b64=t["key"],
        debug=True
    )
    def _on_text(src: str, text: str):
        print(f"[{src}] {text}")
    gw.on_text = _on_text
    gw.connect()
    print(f"Escuchando canal '{canal}'… (q + Enter para salir)")
    try:
        while True:
            if input("").strip().lower() == "q":
                break
    finally:
        gw.disconnect()


# ========= MENÚ INTERACTIVO =========
def interactive_menu(cfg: Dict[str, Any]):
    #canal_actual = cfg["meshtastic"]["channel"]

    while True:
        print("\n" + "="*60)
        print("MENÚ PRINCIPAL")
        print("="*60)
        print("1) ENVIAR mensaje")
        print("2) Escuchar canal actual")
        print("3) Cambiar canal (solo actualizar)")
        print("0) Salir")
        op = input("> ").strip()

        if op == "1":
            mensaje = input("Mensaje: ").strip()
            if not mensaje:
                print("No se ingresó mensaje.")
                continue
            canal_actual = cfg["meshtastic"]["channel"]
            #try:
            send_meshtastic(cfg, canal_actual, mensaje)
            #except Exception as e:
            #    print(f"Error al enviar: {e}")

        elif op == "2":
            try:
                listen_meshtastic(cfg, canal_actual)
            except Exception as e:
                print(f"Error al escuchar: {e}")

        elif op == "3":
            canal_actual = input(f"Nuevo canal [{canal_actual}]: ").strip() or canal_actual
            print(f"Canal actualizado a '{canal_actual}'.")

        elif op == "0":
            print("¡Hasta luego!")
            return

        else:
            print("Opción no válida.")


# ========= CLI OPCIONAL =========
def build_parser(cfg: Dict[str, Any]) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Menú simple Meshtastic")
    sub = p.add_subparsers(dest="mode")

    psend = sub.add_parser("send", help="Enviar mensaje rápido")
    psend.add_argument("--canal", default=cfg["meshtastic"]["channel"])
    psend.add_argument("--mensaje", required=True)

    plist = sub.add_parser("listen", help="Escuchar canal")
    plist.add_argument("--canal", default=cfg["meshtastic"]["channel"])
    return p


def run_non_interactive(cfg: Dict[str, Any], args: argparse.Namespace):
    if args.mode == "send":
        send_meshtastic(cfg, args.canal, args.mensaje)
    elif args.mode == "listen":
        listen_meshtastic(cfg, args.canal)
    else:
        interactive_menu(cfg)


# ========= ENTRADA =========
if __name__ == "__main__":
    cfg = load_config()
    parser = build_parser(cfg)
    ns = parser.parse_args()
    run_non_interactive(cfg, ns)
