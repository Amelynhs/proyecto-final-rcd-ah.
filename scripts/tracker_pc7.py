from tcp import *
from time import *

# ============================================================
# Tracker Dashboard - PC7 (Intranet MAD, VLAN 120 INTERNAL)
# PF RCD 2026-2 - Grupo 1 (ah.net)
# Recibe del Tracker Relay (DMZ) la posicion y actividad de cada
# empleado, genera alertas y las devuelve al Relay (flujo bidireccional),
# que las publica en la vista web http://tracker.ah.net (Browser de PC7).
# ============================================================

RELAY_IP = "2001:1200:EC11:1::30"
RELAY_PORT = 6000
LIMITE_ZONA = 60

cli = {"c": None}
empleados = {}
eventos = []
alertas = []
st = {"rx": 0, "ciclos": 0, "ultimoRx": 0}

def zonaDe(x, y):
    if x >= 70 and y >= 70:
        return "RESTRINGIDA (Data Center)"
    if x < 50 and y < 50:
        return "Oficinas"
    if x >= 50 and y < 50:
        return "Sala de reuniones"
    return "Recepcion / Pasillo"

def registrar(lista, texto, maximo):
    lista.insert(0, texto)
    while len(lista) > maximo:
        lista.pop()

def alerta(texto):
    print("*** ALERTA: " + texto + " ***")
    registrar(alertas, texto, 10)
    try:
        cli["c"].send("ALERTA;" + texto + "\n")
    except:
        print("[DASH] No se pudo notificar la alerta al Relay")

def procesar(linea):
    p = linea.split(";")
    if len(p) < 5:
        return
    bid = p[0]
    x = int(p[1])
    y = int(p[2])
    act = p[3]
    seq = int(p[4])
    e = empleados.get(bid)
    if e is None:
        e = {"act": act, "entrada": -1, "alertado": False}
        empleados[bid] = e
    zona = zonaDe(x, y)
    e["x"] = x
    e["y"] = y
    e["zona"] = zona
    e["seq"] = seq
    texto = bid + " | (" + str(x) + "," + str(y) + ") m | " + zona + " | " + act + " | seq " + str(seq)
    print("[DASH] " + texto)
    registrar(eventos, texto, 15)
    if x >= 70 and y >= 70:
        if e["entrada"] < 0:
            e["entrada"] = seq
            e["alertado"] = False
            print("[DASH] " + bid + " ingreso a zona restringida")
        t = seq - e["entrada"]
        e["tz"] = t
        if t > LIMITE_ZONA and not e["alertado"]:
            alerta(bid + " lleva " + str(t) + " s en zona restringida")
            e["alertado"] = True
    else:
        if e["entrada"] >= 0:
            print("[DASH] " + bid + " salio de la zona restringida tras " + str(seq - e["entrada"]) + " s")
        e["entrada"] = -1
        e["alertado"] = False
        e["tz"] = 0
    if e["act"] == "En reposo" and act == "Alta actividad":
        alerta(bid + " actividad anormal (En reposo -> Alta actividad)")
    e["act"] = act

def onChange(state):
    print("[DASH] Estado TCP con Relay = " + str(state))

def onReceive(data):
    st["ultimoRx"] = st["ciclos"]
    for linea in str(data).split("\n"):
        if len(linea.strip()) > 0:
            st["rx"] += 1
            procesar(linea.strip())

def conectar():
    print("[DASH] Conectando con Tracker Relay [" + RELAY_IP + "]:" + str(RELAY_PORT))
    c = TCPClient()
    c.onConnectionChange(onChange)
    c.onReceive(onReceive)
    c.connect(RELAY_IP, RELAY_PORT)
    cli["c"] = c
    sleep(2)
    try:
        c.send("DASHBOARD PC7 MAD lista\n")
    except:
        pass

def main():
    conectar()
    while True:
        sleep(1)
        st["ciclos"] += 1
        if st["ciclos"] - st["ultimoRx"] > 15:
            print("[DASH] Sin datos del Relay en 15 s, reconectando...")
            try:
                cli["c"].close()
            except:
                pass
            conectar()
            st["ultimoRx"] = st["ciclos"]

if __name__ == "__main__":
    main()
