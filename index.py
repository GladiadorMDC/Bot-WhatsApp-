from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# --- CREDENCIALES ---
VERIFY_TOKEN = "mi_token_secreto_carpinteria"
WHATSAPP_TOKEN = "EAAS11GIEA50BRvJRK4ZBCedOYRy8dfLlEgYc3GoZCT7nigtxPuy7ED5SR5oEAQOSIjgIKEjIgx414CifjihwE8ZBMtHNzfZBwo4Kawmd5GGTxbIuRNXVyZBvbQ0awinCpeCEQ72rALsuLMOpsYhFzQApYXQZC8K9HXsSETxMcQA4hks3654DbdmkHjUGbeMOJZAUQZDZD"
PHONE_NUMBER_ID = "1253869841136312"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzN6pvSQ8UtlqMcgV0tvMwuawMD65p3ICCmDZVH4kwjrx1sLsPUlgj1-o1UKavL88bhag/exec" 

PERFILES = {
    "59178150540": "admin",             
    "591XXXXXXXX": "carpintero",        
    "591YYYYYYYY": "sucursal_lpz",      
    "591ZZZZZZZZ": "sucursal_cbba"      
}

# --- MEMORIA DEL BOT (Para modificaciones) ---
ESTADO_USUARIOS = {} 
# Guardará algo como: {"59178150540": {"modo": "esperando_numero", "item": "Marco 4 (30x42)"}}

ZONA_BOLIVIA = pytz.timezone('America/La_Paz')

def consultar_apps_script(accion, **kwargs):
    """Ahora permite enviar cualquier parámetro extra como 'perfil', 'item', 'valor'"""
    try:
        payload = {"accion": accion}
        payload.update(kwargs)
        response = requests.post(APPS_SCRIPT_URL, json=payload)
        datos = response.json()
        
        # Si pedimos la lista para el menú interactivo, devolvemos el diccionario completo
        if accion == "obtener_menu_lista":
            return datos 
            
        if datos.get("status") == "ok":
            return datos.get("texto")
        else:
            return f"❌ Error: {datos.get('mensaje') or datos.get('texto')}"
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
                "sections": [{"title": "Opciones Disponibles", "rows": rows}]
            }
        }
    }
    requests.post(url, headers=headers, json=data)

def generar_fechas_recientes():
    hoy = datetime.now(ZONA_BOLIVIA)
    fechas = []
    for i in range(7):
        dia = hoy - timedelta(days=i)
        fecha_id = f"fecha_{dia.strftime('%Y-%m-%d')}"
        nombre = f"Hoy ({dia.strftime('%d/%m')})" if i == 0 else f"Ayer ({dia.strftime('%d/%m')})" if i == 1 else dia.strftime('%d/%m/%Y')
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

        # --- MENSAJE DE TEXTO ---
        if mensaje_info['type'] == 'text':
            texto_usuario = mensaje_info['text']['body'].strip()
            
            # 1. Verificar si el usuario estaba en medio de una edición
            if numero_remitente in ESTADO_USUARIOS:
                estado = ESTADO_USUARIOS[numero_remitente]
                if estado["modo"] == "esperando_numero":
                    marco_a_modificar = estado["item"]
                    
                    # Llamamos a Google Script pasándole el número escrito
                    resultado = consultar_apps_script("modificar_item", perfil=rol_usuario, item=marco_a_modificar, valor=texto_usuario)
                    enviar_texto(numero_remitente, resultado)
                    
                    # Limpiamos su memoria para que vuelva a la normalidad
                    del ESTADO_USUARIOS[numero_remitente] 
                    return jsonify({"status": "ok"}), 200
            
            # 2. Si no estaba editando, es un saludo normal
            if rol_usuario == "admin":
                enviar_mensaje_botones(numero_remitente, "👑 *Panel de Administración*", [("btn_admin_control", "Control"), ("btn_admin_trabajos", "Trabajos"), ("btn_admin_inv", "Inventario")])
            elif rol_usuario == "carpintero":
                # Le damos al carpintero su propio botón directo
                enviar_mensaje_botones(numero_remitente, "🔨 *Panel de Carpintero*", [("btn_modificar_lista", "Reportar Avance")])

        # --- INTERACCIONES (BOTONES Y LISTAS) ---
        elif mensaje_info['type'] == 'interactive':
            interaccion = mensaje_info['interactive']
            
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
                    enviar_texto(numero_remitente, "⏳ Procesando historial y ajustes...")
                    resultado = consultar_apps_script("generar_lista_carpinteria")
                    enviar_texto(numero_remitente, resultado)
                    
                elif boton_id == "btn_consolidar_lista":
                    enviar_texto(numero_remitente, "⏳ Guardando la lista actual...")
                    resultado = consultar_apps_script("consolidar_lista")
                    enviar_texto(numero_remitente, resultado)
                
                elif boton_id == "btn_modificar_lista":
                    # Le pedimos a Drive la lista que está guardada
                    enviar_texto(numero_remitente, "⏳ Buscando la lista consolidada...")
                    respuesta_menu = consultar_apps_script("obtener_menu_lista")
                    
                    if respuesta_menu.get("status") == "ok":
                        lista_marcos = respuesta_menu.get("datos", [])
                        opciones_marcos = []
                        
                        # Generamos las opciones del menú dinámicamente
                        for i, item in enumerate(lista_marcos):
                            # Cortamos el título a 24 caracteres por el límite estricto de WhatsApp
                            titulo = item["nombre"][:24] 
                            opciones_marcos.append((f"mod_{i}", titulo))
                            
                        enviar_mensaje_lista(numero_remitente, "✏️ Lista Actual", "Selecciona el marco que deseas afectar:", "Elegir Marco", opciones_marcos)
                    else:
                        enviar_texto(numero_remitente, respuesta_menu.get("texto", "❌ Error al cargar la lista."))
                
                elif boton_id == "btn_admin_inv":
                    enviar_texto(numero_remitente, "⏳ Consultando inventario...")
                    resultado = consultar_apps_script("consultar_inventario", sucursal="Santa Cruz")
                    enviar_texto(numero_remitente, resultado)
                
                elif boton_id == "btn_admin_trabajos":
                    fechas_menu = generar_fechas_recientes()
                    enviar_mensaje_lista(numero_remitente, "📅 Calendario de Trabajos", "Selecciona el día:", "🗓️ Elegir Fecha", fechas_menu)

            # Si seleccionó una opción del Menú de Lista
            elif interaccion['type'] == 'list_reply':
                lista_id = interaccion['list_reply']['id']
                titulo_elegido = interaccion['list_reply']['title']
                
                if lista_id.startswith("fecha_"):
                    fecha_elegida = lista_id.replace("fecha_", "")
                    enviar_texto(numero_remitente, f"⏳ Buscando registros del {fecha_elegida}...")
                    resultado = consultar_apps_script("consultar_trabajos", fecha=fecha_elegida)
                    enviar_texto(numero_remitente, resultado)

                elif lista_id.startswith("mod_"):
                    # Activamos el modo "esperando_numero" para este usuario en específico
                    ESTADO_USUARIOS[numero_remitente] = {"modo": "esperando_numero", "item": titulo_elegido}
                    
                    if rol_usuario == "admin":
                        enviar_texto(numero_remitente, f"Has seleccionado *{titulo_elegido}*.\n\nEscribe el *nuevo total faltante* que quieres fijar. (Ej: 15)")
                    elif rol_usuario == "carpintero":
                        enviar_texto(numero_remitente, f"Has seleccionado *{titulo_elegido}*.\n\nEscribe *cuántos cuadros terminaste hoy* para reportarlos. (Ej: 5)")

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
