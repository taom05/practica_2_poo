import tkinter as tk
from tkinter import messagebox
import json
import os
from tkintermapview import TkinterMapView

from main import load_config
from dispositivo import Dispositivo
from meshtastic_client import MeshtasticGateway
cfg = load_config()
disp = Dispositivo(nombre="Nodo GUI Mapa", protocolo="meshtastic")

gw_rx = None
ultimo_enviado = None

def parsear_posicion_meshtastic(linea: str):
    """
    Parsea mensajes Meshtastic con formato:
      latitude_i: XXXXX longitude_i: XXXXX altitude: XXX ...
    Funciona aunque vengan en varias líneas y con distintos nombres de altitud.
    """
    linea = linea.replace("\n", " ").replace("\r", " ")
    partes = linea.split()
    datos = {}
    clave_pendiente = None

    for p in partes:
        # caso: "latitude_i:"
        if p.endswith(":"):
            clave_pendiente = p[:-1]

        # caso: "latitude_i:426814500"
        elif ":" in p:
            k, v = p.split(":", 1)
            datos[k] = v
            clave_pendiente = None

        else:
            if clave_pendiente:
                datos[clave_pendiente] = p
                clave_pendiente = None

    if "latitude_i" in datos and "longitude_i" in datos:
        try:
            lat_i = int(datos["latitude_i"])
            lon_i = int(datos["longitude_i"])

            lat = lat_i / 1e7
            lon = lon_i / 1e7
            alt_raw = (
                datos.get("altitude_hae")
                or datos.get("altitude")
                or datos.get("alt")
                or "0"
            )
            alt = float(alt_raw)

            return lat, lon, alt
        except Exception:
            return None

    return None
def poner_coordenadas(lat, lon, alt=0.0):
    lat_entry.delete(0, tk.END)
    lat_entry.insert(0, f"{lat:.6f}")
    lon_entry.delete(0, tk.END)
    lon_entry.insert(0, f"{lon:.6f}")
    alt_entry.delete(0, tk.END)
    alt_entry.insert(0, str(alt))


def mostrar_en_mapa(lat, lon):
    map_widget.set_position(lat, lon)
    map_widget.set_marker(lat, lon, text="Nodo")

def al_llegar_texto(topic, texto):
    global ultimo_enviado

    print("Mensaje bruto recibido:", texto)

    if ultimo_enviado and texto == ultimo_enviado:
        return
    try:
        payload = json.loads(texto)
        print(type(payload))

        lat = payload.get("lat")
        lon = payload.get("long") or payload.get("lon") or payload.get("longitude")
        alt = payload.get("alt", 0.0)

        if lat is not None and lon is not None:

            def _update_json():
                poner_coordenadas(lat, lon, alt)
                mostrar_en_mapa(lat, lon)
                estado_label.config(text=f"Posición (JSON) recibida", fg="blue")
                disp.registrar_posicion(lat, lon, alt)
                disp.guardar_datos()

            root.after(0, _update_json)

        return

    except:
        print("No es JSON válido. Intentando formato Meshtastic...")

    # ----- 2) Intentar formato Meshtastic -----
    pos = parsear_posicion_meshtastic(texto)
    if pos is None:
        print("No es JSON ni formato Meshtastic reconocible.")
        return

    lat, lon, alt = pos

    def _update_mesh():
        poner_coordenadas(lat, lon, alt)
        mostrar_en_mapa(lat, lon)
        estado_label.config(text=f"Posición (Meshtastic) recibida", fg="blue")
        disp.registrar_posicion(lat, lon, alt)
        disp.guardar_datos()

    root.after(0, _update_mesh)


# ===================== ENVÍO =====================
def enviar_mensaje_y_pos():
    global ultimo_enviado

    mensaje = msg_entry.get().strip()
    lat_txt = lat_entry.get().strip()
    lon_txt = lon_entry.get().strip()
    alt_txt = alt_entry.get().strip() or "0"

    # obtener lat/lon del mapa si campos vacíos
    if not lat_txt or not lon_txt:
        lat, lon = map_widget.get_position()
    else:
        lat = float(lat_txt)
        lon = float(lon_txt)

    alt = float(alt_txt)

    payload = {
        "msg": mensaje,
        "lat": lat,
        "long": lon,
        "alt": alt
    }

    texto = json.dumps(payload, ensure_ascii=False)
    ultimo_enviado = texto

    try:
        t = cfg["meshtastic"]
        gw_tx = MeshtasticGateway(
            broker=t["broker"],
            port=t["port"],
            username=t["username"],
            password=t["password"],
            root_topic=t["root_topic"],
            channel=t["channel"],
            key_b64=t["key"],
            debug=True
        )
        gw_tx.connect()
        gw_tx.send_text(texto)
        gw_tx.disconnect()

        estado_label.config(text=f"Enviado correctamente", fg="green")

        mostrar_en_mapa(lat, lon)
        poner_coordenadas(lat, lon, alt)

        disp.registrar_mensaje(mensaje or "[sin texto]",
                               origen="GUI mapa",
                               destino=t["channel"])
        disp.registrar_posicion(lat, lon, alt)
        disp.guardar_datos()

    except Exception as e:
        estado_label.config(text=f"Error al enviar: {e}", fg="red")


# ===================== GUI =====================
root = tk.Tk()
root.title("Interfaz con mapa  Práctica 2 POO")
root.geometry("900x500")

left = tk.Frame(root)
left.pack(side="left", fill="y", padx=10, pady=10)

tk.Label(left, text="Canal (config):").pack(anchor="w")
canal_entry = tk.Entry(left, width=30)
canal_entry.insert(0, cfg["meshtastic"]["channel"])
canal_entry.config(state="readonly")
canal_entry.pack(anchor="w", pady=(0, 10))

tk.Label(left, text="Mensaje:").pack(anchor="w")
msg_entry = tk.Entry(left, width=30)
msg_entry.pack(anchor="w", pady=(0, 10))

tk.Label(left, text="Latitud:").pack(anchor="w")
lat_entry = tk.Entry(left, width=20)
lat_entry.pack(anchor="w")

tk.Label(left, text="Longitud:").pack(anchor="w")
lon_entry = tk.Entry(left, width=20)
lon_entry.pack(anchor="w")

tk.Label(left, text="Altura (m):").pack(anchor="w")
alt_entry = tk.Entry(left, width=20)
alt_entry.insert(0, "0")
alt_entry.pack(anchor="w", pady=(0, 10))

tk.Button(
    left,
    text="Enviar mensaje + posición",
    bg="#4CAF50",
    fg="white",
    command=enviar_mensaje_y_pos
).pack(anchor="w", pady=5)

estado_label = tk.Label(left, text="Estado: esperando acción...", fg="gray")
estado_label.pack(anchor="w", pady=10)

# mapa
right = tk.Frame(root)
right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

map_widget = TkinterMapView(right, width=600, height=450, corner_radius=0)
map_widget.pack(fill="both", expand=True)

# posición inicial
map_widget.set_position(31.9539, 35.9106)
map_widget.set_zoom(6)

def iniciar_gateway_rx():
    global gw_rx
    try:
        t = cfg["meshtastic"]
        gw_rx = MeshtasticGateway(
            broker=t["broker"],
            port=t["port"],
            username=t["username"],
            password=t["password"],
            root_topic=t["root_topic"],
            channel=t["channel"],
            key_b64=t["key"],
            debug=True
        )
        gw_rx.on_text = al_llegar_texto
        gw_rx.connect()
        estado_label.config(text="Conectado y escuchando…", fg="green")
    except Exception as e:
        estado_label.config(text=f"Error al conectar: {e}", fg="orange")


def cerrar():
    try:
        if gw_rx:
            gw_rx.disconnect()
    except:
        pass
    root.destroy()
    
iniciar_gateway_rx()
root.protocol("WM_DELETE_WINDOW", cerrar)
root.mainloop()
