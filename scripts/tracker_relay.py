from tcp import *
from http import *
from time import *

# ============================================================
# Tracker Relay - Tracker_Server (DMZ, 2001:1200:EC11:1::30)
# PF RCD 2026-2 - Grupo 1 (ah.net)
# - TCP/5000: recibe los paquetes de la Tracker App (PC4, BOG)
# - TCP/6000: reenvia cada paquete a la Tracker Dashboard (PC7, MAD)
#             y recibe de vuelta las alertas que esta genera
# - HTTP/80 : vista web del Dashboard -> http://tracker.ah.net
# Formato del paquete: ID;X;Y;ESTADO;SEQ\n
# ============================================================

APP_PORT = 5000
DASH_PORT = 6000

appServer = TCPServer()
dashServer = TCPServer()
dashboards = []
stats = {"rx": 0, "tx": 0}
ultimo = {}
eventos = []
alertas = []

def registrar(lista, texto, maximo):
    lista.insert(0, texto)
    while len(lista) > maximo:
        lista.pop()

def zonaDe(x, y):
    if x >= 70 and y >= 70:
        return "RESTRINGIDA (Data Center)"
    if x < 50 and y < 50:
        return "Oficinas"
    if x >= 50 and y < 50:
        return "Sala de reuniones"
    return "Recepcion / Pasillo"

def onNewDashboard(client):
    print("[RELAY] Dashboard conectada desde " + client.remoteIP())
    dashboards.append(client)
    def onDashChange(state):
        print("[RELAY] Dashboard " + client.remoteIP() + " estado TCP=" + str(state))
    def onDashReceive(data):
        for linea in str(data).split("\n"):
            linea = linea.strip()
            if linea.find("ALERTA;") == 0:
                registrar(alertas, linea[7:], 10)
                print("[RELAY] <- Dashboard ALERTA: " + linea[7:])
            elif len(linea) > 0:
                print("[RELAY] Dashboard dice: " + linea)
    client.onConnectionChange(onDashChange)
    client.onReceive(onDashReceive)

def reenviar(paquete):
    p = paquete.strip().split(";")
    if len(p) >= 5:
        ultimo[p[0]] = p
        registrar(eventos, paquete.strip(), 12)
    if len(dashboards) == 0:
        print("[RELAY] Sin Dashboard conectada, paquete descartado")
        return
    for d in list(dashboards):
        try:
            d.send(paquete)
        except:
            dashboards.remove(d)
            print("[RELAY] Dashboard desconectada, se retira de la lista")
    stats["tx"] += 1
    print("[RELAY] -> Dashboard (#" + str(stats["tx"]) + ") " + paquete.strip())

def onNewApp(client):
    print("[RELAY] Tracker App conectada desde " + client.remoteIP())
    def onAppChange(state):
        print("[RELAY] App " + client.remoteIP() + " estado TCP=" + str(state))
    def onAppReceive(data):
        stats["rx"] += 1
        texto = str(data)
        print("[RELAY] <- App (#" + str(stats["rx"]) + ") " + texto.strip())
        try:
            client.send("ACK " + str(stats["rx"]) + "\n")
        except:
            pass
        for linea in texto.split("\n"):
            if len(linea.strip()) > 0:
                reenviar(linea.strip() + "\n")
    client.onConnectionChange(onAppChange)
    client.onReceive(onAppReceive)

def mapa():
    # Plano 10x10 (celdas de 10 m): '#' zona restringida, '.' libre, 'E' empleado
    h = ""
    fila = 9
    while fila >= 0:
        col = 0
        while col < 10:
            c = "."
            if col >= 7 and fila >= 7:
                c = "#"
            for bid in ultimo:
                p = ultimo[bid]
                if int(int(p[1]) / 10.01) == col and int(int(p[2]) / 10.01) == fila:
                    c = "E"
            h += c + " "
            col += 1
        h += "\n"
        fila -= 1
    return h

def pagina():
    # Pagina compacta (< 1 KB) para que cruce el tunel 6in4 + IPsec sin fragmentar
    h = "<html><head><meta http-equiv='refresh' content='2'></head><body>"
    h += "<h3>Employee Tracker - ah.net</h3>"
    h += "<p>Rx " + str(stats["rx"]) + " / Tx " + str(stats["tx"]) + "</p>"
    for bid in ultimo:
        p = ultimo[bid]
        h += "<p><b>" + bid + "</b> (" + p[1] + "," + p[2] + ") m - " + zonaDe(int(p[1]), int(p[2])) + " - " + p[3] + " - seq " + p[4] + "</p>"
    h += "<pre>" + mapa() + "</pre>"
    h += "<p><b>Alertas (Dashboard PC7):</b><br>"
    if len(alertas) == 0:
        h += "Sin alertas"
    i = 0
    while i < len(alertas) and i < 3:
        h += "<font color='red'>" + alertas[i] + "</font><br>"
        i += 1
    return h + "</p></body></html>"

def onRouteAll(url, response):
    response.setContentType("text/html")
    response.send(pagina())

def main():
    appServer.onNewClient(onNewApp)
    dashServer.onNewClient(onNewDashboard)
    print("[RELAY] Escuchando Tracker App en TCP/" + str(APP_PORT) + ": " + str(appServer.listen(APP_PORT)))
    print("[RELAY] Escuchando Dashboards en TCP/" + str(DASH_PORT) + ": " + str(dashServer.listen(DASH_PORT)))
    HTTPServer.route("/*", onRouteAll)
    print("[RELAY] Vista web en HTTP/80: " + str(HTTPServer.start(80)))
    while True:
        sleep(3600)

if __name__ == "__main__":
    main()
