import tkinter as tk
from tkinter import messagebox
import json
import os

# نستخدم نفس الدوال من main.py
from main import load_config, send_meshtastic
from dispositivo import Dispositivo

# نحمّل نفس الـ cfg اللي يستعمله main.py
cfg = load_config()
disp = Dispositivo(nombre="Nodo GUI", protocolo="meshtastic")

def enviar_mensaje():
    """Enviar mensaje usando EXACTAMENTE la misma lógica que el menú."""
    canal_config = cfg["meshtastic"]["channel"]
    mensaje = mensaje_entry.get().strip()

    if not mensaje:
        messagebox.showwarning("Advertencia", "Por favor, escribe un mensaje.")
        return

    try:
        # نستخدم نفس الدالة اللي المنيو يستخدمها
        send_meshtastic(cfg, canal_config, mensaje)

        estado_label.config(
            text=f"Enviado en canal '{canal_config}'",
            fg="green"
        )
        # نسجّل الرسالة محلياً
        disp.registrar_mensaje(mensaje, origen="GUI", destino=canal_config)
        disp.guardar_datos()

    except Exception as e:
        estado_label.config(text=f"Error: {e}", fg="red")

# ----------- interfaz gráfica -----------
root = tk.Tk()
root.title("Interfaz Meshtastic - Practica 2 POO")
root.geometry("400x230")
root.resizable(False, False)

# canal (solo información, نفس الموجود في config)
tk.Label(root, text="Canal (desde config.json):").pack(anchor="w", padx=10, pady=(10, 0))
canal_entry = tk.Entry(root, width=40)
canal_entry.insert(0, cfg["meshtastic"]["channel"])
canal_entry.config(state="readonly")
canal_entry.pack(padx=10, pady=2)

# mensaje
tk.Label(root, text="Mensaje:").pack(anchor="w", padx=10, pady=(10, 0))
mensaje_entry = tk.Entry(root, width=40)
mensaje_entry.pack(padx=10, pady=2)

# botón
tk.Button(
    root,
    text="Enviar mensaje",
    command=enviar_mensaje,
    bg="#4CAF91",
    fg="white"
).pack(pady=10)

# etiqueta estado
estado_label = tk.Label(root, text="Estado: esperando acción...", fg="gray")
estado_label.pack(pady=(5, 0))
root.mainloop()
