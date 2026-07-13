from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# --- CREDENCIALES ---
VERIFY_TOKEN = "mi_token_secreto_carpinteria"
WHATSAPP_TOKEN = "EAAS11GIEA50BRvJRK4ZBCedOYRy8dfLlEgYc3GoZCT7nigtxPuy7ED5SR5oEAQOSIjgIKEjIgx414CifjihwE8ZBMtHNzfZBwo4Kawmd5GGTxbIuRNXVyZBvbQ0awinCpeCEQ72rALsuLMOpsYhFzQApYXQZC8K9HXsSETxMcQA4hks3654DbdmkHjUGbeMOJZAUQZDZD"
PHONE_NUMBER_ID = "1253869841136312"

# 👇 PEGA TU NUEVA URL DE APPS SCRIPT AQUÍ 👇
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwfRQZa-7UMbtueNj9E1fVH_VYraWSDx6ReYt249B1MSzZpKsAMJuGehXxZWoh0npkAPA/exec" 

PERFILES = {
    "59178150540": "admin",             
    "591XXXXXXXX": "carpintero",        
    "591YYYYYYYY": "sucursal_lpz",      
    "591ZZZZZZZZ": "sucursal_cbba"      
}

# Zona horaria de Bolivia
ZONA_BOLIVIA = pytz.timezone('America/La_Paz')

def consultar_apps_script(accion, sucursal="", fecha=""):
    try:
        payload = {"accion": accion, "sucursal": sucursal, "fecha": fecha}
        response = requests.post(APPS_SCRIPT_URL, json=payload)
        datos = response.json()
        if datos.get("status") == "ok":
            return datos.get("texto")
        else:
            return f"❌ Error: {datos.get('mensaje')}"
    except Exception as e:
        return f"❌ Error de conexión: {e}"

def enviar_texto(numero, texto):
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    requests.post(url, headers=headers, json={"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": texto}})

def enviar_mensaje_botones(numero, texto_body, botones_config):
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    botones = [{"type": "reply", "reply": {"id": b[0], "title": b[1]}} for b in botones_config]
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {"type": "button", "body": {"text": texto_body}, "action": {"buttons": botones}}
    }
    requests.post(url, headers=headers, json=data)

def enviar_mensaje_lista(numero, titulo, descripcion, boton_texto, opciones):
    """Genera un menú desplegable estilo calendario para elegir fechas"""
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    
    rows = [{"id": op[0], "title": op[1]} for op in opciones]
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": titulo},
            "body": {"text": descripcion},
            "action": {
                "button": boton_texto,
                "sections": [{"title": "Fechas Disponibles", "rows": rows}]
            }
        }
    }
    requests.post(url, headers=headers, json=data)

def generar_fechas_recientes():
    """Calcula los últimos 7 días automáticamente"""
    hoy = datetime.now(ZONA_BOLIVIA)
    fechas = []
    for i in range(7):
        dia = hoy - timedelta(days=i)
        fecha_id = f"fecha_{dia.strftime('%Y-%m-%d')}"
        if i == 0:
            nombre = f"Hoy ({dia.strftime('%d/%m')})"
        elif i == 1:
            nombre = f"Ayer ({dia.strftime('%d/%m')})"
        else:
            nombre = dia.strftime('%d/%m/%Y')
        fechas.append((fecha_id, nombre))
    return fechas

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == VERIFY_TOKEN:
            return request.args.get('hub.challenge'), 200
        return 'Bot activo', 200

    body = request.get_json()
    if body.get('object') and body.get('entry') and body['entry'][0].get('changes') and body['entry'][0]['changes'][0].get('value').get('messages'):
        mensaje_info = body['entry'][0]['changes'][0]['value']['messages'][0]
        numero_remitente = mensaje_info['from']
        rol_usuario = PERFILES.get(numero_remitente, "desconocido")

        if rol_usuario == "desconocido":
            enviar_texto(numero_remitente, "⛔ Acceso denegado.")
            return jsonify({"status": "ok"}), 200

        # --- MENSAJE INICIAL DE TEXTO ---
        if mensaje_info['type'] == 'text':
            if rol_usuario == "admin":
                enviar_mensaje_botones(numero_remitente, "👑 *Panel de Administración*", [("btn_admin_control", "Control"), ("btn_admin_trabajos", "Trabajos"), ("btn_admin_inv", "Inventario")])

        # --- INTERACCIONES (BOTONES Y LISTAS) ---
        elif mensaje_info['type'] == 'interactive':
            interaccion = mensaje_info['interactive']
            
            # Si tocó un Botón normal
            if interaccion['type'] == 'button_reply':
                boton_id = interaccion['button_reply']['id']
                
                if boton_id == "btn_admin_control":
                    enviar_mensaje_botones(numero_remitente, "⚙️ *Control de Listas*", [("btn_ctrl_carpinteria", "L. Carpintería"), ("btn_ctrl_envios", "L. Envíos")])
                elif boton_id == "btn_ctrl_carpinteria":
                    enviar_mensaje_botones(numero_remitente, "🪵 *Lista de Carpintería Semanal*\n¿Qué deseas hacer?", [
                        ("btn_crear_lista_carp", "Crear Nueva"),
                        ("btn_modificar_lista", "Modificar Lista"),
                        ("btn_consolidar_lista", "Consolidar Lista")
                    ])
                elif boton_id == "btn_crear_lista_carp":
                    enviar_texto(numero_remitente, "⏳ Procesando historial de últimos 30 días y ajustes...")
                    resultado = consultar_apps_script("generar_lista_carpinteria")
                    enviar_texto(numero_remitente, resultado)
                # --- NUEVOS BOTONES DE LISTA ---
                elif boton_id == "btn_modificar_lista":
                    # Usamos una lista temporal hardcodeada por ahora para la interfaz, luego la conectaremos a la DB
                    opciones_marcos = [
                        ("mod_marco4_30x42", "Marco 4 (30x42)"),
                        ("mod_marcoA2_16x22", "Marco A2 (16x22)"),
                        ("mod_marco4_50x40", "Marco 4 (50x40)"),
                        ("mod_marco3_30x42", "Marco 3 (30x42)"),
                        ("mod_marcoB2_20x27", "Marco B2 (20x27)")
                    ]
                    enviar_mensaje_lista(numero_remitente, "✏️ Modificar Cantidad", "Selecciona el marco que deseas ajustar:", "Elegir Marco", opciones_marcos)
                    
                elif boton_id == "btn_consolidar_lista":
                    enviar_texto(numero_remitente, "⏳ Consolidando la lista actual en la base de datos...")
                    # Aquí irá la llamada a consultar_apps_script("consolidar_lista")
                    # resultado = consultar_apps_script("consolidar_lista")
                    # enviar_texto(numero_remitente, resultado)
                
                # --- AQUÍ ESTÁ LA MAGIA DEL INVENTARIO ---
                elif boton_id == "btn_admin_inv":
                    enviar_texto(numero_remitente, "⏳ Consultando inventario en tiempo real...")
                    resultado = consultar_apps_script("consultar_inventario", sucursal="Santa Cruz")
                    enviar_texto(numero_remitente, resultado)
                
                # --- AQUÍ ESTÁ LA MAGIA DEL "CALENDARIO" ---
                elif boton_id == "btn_admin_trabajos":
                    fechas_menu = generar_fechas_recientes()
                    enviar_mensaje_lista(numero_remitente, "📅 Calendario de Trabajos", "Selecciona el día que deseas consultar:", "🗓️ Elegir Fecha", fechas_menu)

            # Si seleccionó una opción del Menú de Lista
            elif interaccion['type'] == 'list_reply':
                lista_id = interaccion['list_reply']['id']
                
                # ... (tu código del calendario fecha_) ...

                elif lista_id.startswith("mod_"):
                    marco_elegido = interaccion['list_reply']['title'] # Obtenemos el nombre "Marco 4 (30x42)"
                    enviar_texto(numero_remitente, f"Has seleccionado *{marco_elegido}*.\n\nEscribe el *nuevo número* que deseas asignarle. (Solo el número).")
                    
                    # (Nota de diseño: Aquí necesitaremos agregar una variable global o conectar a una base de datos 
                    # para recordar qué marco eligió el usuario cuando responda con el número en el próximo mensaje).
                
                if lista_id.startswith("fecha_"):
                    fecha_elegida = lista_id.replace("fecha_", "") # Extraemos el '2026-07-12'
                    enviar_texto(numero_remitente, f"⏳ Buscando registros del {fecha_elegida}...")
                    resultado = consultar_apps_script("consultar_trabajos", fecha=fecha_elegida)
                    enviar_texto(numero_remitente, resultado)

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
