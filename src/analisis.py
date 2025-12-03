from almacen import Almacen
from dispositivo import Dispositivo
def demo_almacen():
    almac_str = Almacen[str]()
    almac_str.agregar("hola")
    almac_str.agregar("adiós")
    print("Último string:", almac_str.ultimo())

    almac_disp = Almacen[Dispositivo]()
    d = Dispositivo(nombre="Nodo A", protocolo="meshtastic")
    almac_disp.agregar(d)
    print("Último dispositivo:", almac_disp.ultimo().nombre)

if __name__ == "__main__":
    demo_almacen()
