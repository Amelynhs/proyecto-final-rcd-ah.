from tcp import *
from time import *
import random

# ============================================================
# Tracker App - PC4 (Intranet BOG, VLAN 20 INTERNAL)
# PF RCD 2026-2 - Grupo 1 (ah.net)
# Simula la deteccion via Bluetooth (BLE) de un beacon de empleado
# y envia cada segundo ID;X;Y;ESTADO;SEQ al Tracker Relay (DMZ).
# ============================================================

RELAY_IP = "2001:1200:EC11:1::30"
RELAY_PORT = 5000
BEACON_ID = "BEACON-EMP-001"
ESTADOS = ["En reposo", "En movimiento", "Alta actividad"]

cli = {"c": None}
st = {"seq": 0, "ack": 0, "x": 20, "y": 20}

def onChange(state):
    print("[APP] Estado TCP con Relay = " + str(state))

def onReceive(data):
    st["ack"] = st["seq"]
    print("[APP] Relay: " + str(data).strip())

def limitar(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v

def detectarBeacon():
    # Escenario simulado de 150 s: 60 s recorriendo el edificio,
    # 80 s dentro de la zona restringida (x>=70, y>=70) y 10 s de salida.
    fase = st["seq"] % 150
    if fase < 60 or fase >= 140:
        st["x"] = limitar(st["x"] + random.randint(-8, 8), 0, 65)
        st["y"] = limitar(st["y"] + random.randint(-8, 8), 0, 65)
    else:
        st["x"] = limitar(st["x"] + random.randint(-3, 6), 72, 100)
        st["y"] = limitar(st["y"] + random.randint(-3, 6), 72, 100)
    actividad = ESTADOS[random.randint(0, 2)]
    st["seq"] += 1
    return BEACON_ID + ";" + str(st["x"]) + ";" + str(st["y"]) + ";" + actividad + ";" + str(st["seq"]) + "\n"

def conectar():
    print("[APP] Conectando con Tracker Relay [" + RELAY_IP + "]:" + str(RELAY_PORT))
    c = TCPClient()
    c.onConnectionChange(onChange)
    c.onReceive(onReceive)
    c.connect(RELAY_IP, RELAY_PORT)
    cli["c"] = c

def main():
    conectar()
    while True:
        sleep(1)
        paquete = detectarBeacon()
        try:
            cli["c"].send(paquete)
        except:
            print("[APP] Error enviando al Relay")
        print("[APP] BLE detectado -> " + paquete.strip())
        if st["seq"] - st["ack"] > 5:
            print("[APP] Sin ACK del Relay, reconectando...")
            try:
                cli["c"].close()
            except:
                pass
            conectar()
            st["ack"] = st["seq"]

if __name__ == "__main__":
    main()
