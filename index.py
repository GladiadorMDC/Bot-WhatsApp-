from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# --- CREDENCIALES ---
VERIFY_TOKEN = "mi_token_secreto_carpinteria"
WHATSAPP_TOKEN = "EAAS11GIEA50BRvJRK4ZBCedOYRy8dfLlEgYc3GoZCT7nigtxPuy7ED5SR5oEAQOSIjgIKEjIgx414CifjihwE8ZBMtHNzfZBwo4Kawmd5GGTxbIuRNXVyZBvbQ0awinCpeCEQ72rALsuLMOpsYhFzQApYXQZC8K9HXsSETxMcQA4hks3654DbdmkHjUGbeMOJZAUQZDZD"
PHONE_NUMBER_ID = "1253869841136312"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyVfiffGUZaQfg6AgLl8oQMYGY-_HCV-EjxhC6ROAOsnqOkgmklw-QAzk1UjjS4b3x0uA/exec" 

# --- GESTIÓN ESCALABLE DE PERFILES ---
# Separa múltiples números con un guion: "591XXXX-591YYYY-591ZZZZ"
PERFILES = {
    "admin": "59178120249-59178505063",             
    "carpintero": "59175035455",        
    "sucursal_scz": "59178150540",      
    "sucursal_lpz": "591ZZZZZZZZ",
    "sucursal_cba": "591AAAAAAAA"
}

def obtener_rol(numero):
    for rol, numeros_str in PERFILES.items():
        if numero in numeros_str.split('-'):
            return rol
    return "desconocido"

# --- MEMORIA DEL SISTEMA ---
ESTADO_USUARIOS = {} 

ZONA_BOLIVIA = pytz.timezone('America/La_Paz')

def consultar_apps_script(accion, **kwargs):
    try:
        payload = {"accion": accion}
        payload.update(kwargs)
        response = requests.post(APPS_SCRIPT_URL, json=payload)
        datos = response.json()
        
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

def generar_semanas_recientes():
    semanas = []
    for i in range(4):
        semanas.append((f"semana_{i}", f"Hace {i} semanas" if i > 0 else "Semana Actual"))
    return semanas

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
        
        rol_usuario = obtener_rol(numero_remitente)

        if rol_usuario == "desconocido":
            enviar_texto(numero_remitente, "⛔ Acceso denegado. Número no registrado.")
            return jsonify({"status": "ok"}), 200

        # --- MENSAJE DE TEXTO ---
        if mensaje_info['type'] == 'text':
            texto_usuario = mensaje_info['text']['body'].strip()
            
            # 1. Modos de Edición (Carpintero / Admin)
            if numero_remitente in ESTADO_USUARIOS:
                estado = ESTADO_USUARIOS[numero_remitente]
                
                # Modificando la lista oficial
                if estado["modo"] == "esperando_numero":
                    marco_a_modificar = estado["item"]
                    resultado = consultar_apps_script("modificar_item", perfil=rol_usuario, item=marco_a_modificar, valor=texto_usuario)
                    enviar_texto(numero_remitente, resultado)
                    del ESTADO_USUARIOS[numero_remitente] 
                    return jsonify({"status": "ok"}), 200
                
                # Añadiendo trabajo extra (Paso 1: Recibe nombre, pide cantidad)
                elif estado["modo"] == "esperando_nombre_extra":
                    ESTADO_USUARIOS[numero_remitente] = {"modo": "esperando_cantidad_extra", "item": texto_usuario}
                    enviar_texto(numero_remitente, f"Marco extra: *{texto_usuario}*.\n¿Cuántos terminaste? (Solo el número)")
                    return jsonify({"status": "ok"}), 200
                
                # Añadiendo trabajo extra (Paso 2: Recibe cantidad y envía a DB)
                elif estado["modo"] == "esperando_cantidad_extra":
                    marco_extra = estado["item"]
                    resultado = consultar_apps_script("registrar_trabajo_extra", item=marco_extra, valor=texto_usuario)
                    enviar_texto(numero_remitente, resultado)
                    del ESTADO_USUARIOS[numero_remitente] 
                    return jsonify({"status": "ok"}), 200
            
            # 2. Comando Sumar Personalizado (Admin)
            if texto_usuario.lower().startswith("sumar ") and rol_usuario == "admin":
                partes = texto_usuario.split()
                if len(partes) == 2 and partes[1].isdigit():
                    dias = int(partes[1])
                    enviar_texto(numero_remitente, f"⏳ Sumando historial de los últimos {dias} días...")
                    resultado = consultar_apps_script("sumar_historial", dias=dias)
                    enviar_texto(numero_remitente, resultado)
                    return jsonify({"status": "ok"}), 200

            # 3. Menús Principales por Perfil
            if rol_usuario == "admin":
                enviar_mensaje_botones(numero_remitente, "👑 *Panel de Administración*", [("btn_admin_control", "Control"), ("btn_admin_trabajos", "Trabajos"), ("btn_menu_inventarios", "Inventarios")])
            
            elif rol_usuario == "carpintero":
                enviar_mensaje_botones(numero_remitente, "🔨 *Panel de Carpintero*", [("btn_modificar_lista", "Reportar de la Lista"), ("btn_trabajo_extra", "Añadir Trabajo Extra")])
            
            # Perfiles asilados de sucursales (Directo al grano)
            elif rol_usuario == "sucursal_scz":
                enviar_texto(numero_remitente, "⏳ Obteniendo inventario de Santa Cruz...")
                resultado = consultar_apps_script("consultar_inventario", sucursal="Santa Cruz")
                enviar_texto(numero_remitente, resultado)
            elif rol_usuario == "sucursal_lpz":
                enviar_texto(numero_remitente, "⏳ Obteniendo inventario de La Paz...")
                resultado = consultar_apps_script("consultar_inventario", sucursal="La Paz")
                enviar_texto(numero_remitente, resultado)
            elif rol_usuario == "sucursal_cba":
                enviar_texto(numero_remitente, "⏳ Obteniendo inventario de Cochabamba...")
                resultado = consultar_apps_script("consultar_inventario", sucursal="Cochabamba")
                enviar_texto(numero_remitente, resultado)

        # --- INTERACCIONES (BOTONES Y LISTAS) ---
        elif mensaje_info['type'] == 'interactive':
            interaccion = mensaje_info['interactive']
            
            if interaccion['type'] == 'button_reply':
                boton_id = interaccion['button_reply']['id']
                
                if boton_id == "btn_admin_control":
                    enviar_mensaje_botones(numero_remitente, "⚙️ *Control de Listas*", [("btn_ctrl_carpinteria", "L. Carpintería"), ("btn_ctrl_prod", "L. Producción"), ("btn_ctrl_envios", "L. Envíos")])
                
                # --- LISTA DE CARPINTERIA ---
                elif boton_id == "btn_ctrl_carpinteria":
                    enviar_mensaje_botones(numero_remitente, "🪵 *Gestión de Lista*\n¿Qué deseas hacer?", [("btn_ver_lista", "Ver Lista"), ("btn_modificar_lista", "Modificar Lista"), ("btn_preguntar_crear", "Crear Nueva")])
                
                elif boton_id == "btn_preguntar_crear":
                    enviar_mensaje_botones(numero_remitente, "⚠️ *¡ATENCIÓN!*\n¿Estás seguro que deseas eliminar la lista anterior por una nueva lista?", [("btn_crear_lista_carp", "✅ Sí, crear nueva"), ("btn_cancelar_accion", "❌ No, cancelar")])
                
                elif boton_id == "btn_cancelar_accion":
                    enviar_texto(numero_remitente, "Operación cancelada. La lista actual se mantiene intacta.")
                
                elif boton_id == "btn_crear_lista_carp":
                    enviar_texto(numero_remitente, "⏳ Procesando historial y creando nueva lista...")
                    resultado = consultar_apps_script("generar_lista_carpinteria")
                    enviar_texto(numero_remitente, resultado)
                
                elif boton_id == "btn_ver_lista":
                    enviar_texto(numero_remitente, "⏳ Obteniendo lista consolidada...")
                    resultado = consultar_apps_script("ver_lista_actual")
                    enviar_texto(numero_remitente, resultado)
                
                elif boton_id == "btn_modificar_lista":
                    enviar_texto(numero_remitente, "⏳ Buscando la lista activa...")
                    respuesta_menu = consultar_apps_script("obtener_menu_lista")
                    
                    if respuesta_menu.get("status") == "ok":
                        lista_marcos = respuesta_menu.get("datos", [])
                        opciones_marcos = []
                        for i, item in enumerate(lista_marcos):
                            titulo = item["nombre"][:24] 
                            opciones_marcos.append((f"mod_{i}", titulo))
                        enviar_mensaje_lista(numero_remitente, "✏️ Lista Actual", "Selecciona el marco que deseas afectar:", "Elegir Marco", opciones_marcos)
                    else:
                        enviar_texto(numero_remitente, respuesta_menu.get("texto", "❌ Error al cargar la lista."))
                
                # --- LISTA DE PRODUCCIÓN (SEMANAL) ---
                elif boton_id == "btn_ctrl_prod":
                    semanas_menu = generar_semanas_recientes()
                    enviar_mensaje_lista(numero_remitente, "📈 Lista de Producción", "Elige la semana a consultar:", "🗓️ Elegir Semana", semanas_menu)

                # --- TRABAJOS EXTRA (CARPINTERO) ---
                elif boton_id == "btn_trabajo_extra":
                    ESTADO_USUARIOS[numero_remitente] = {"modo": "esperando_nombre_extra"}
                    enviar_texto(numero_remitente, "➕ *Trabajo Extra*\nEscribe el Nombre y Tamaño del marco que fabricaste. (Ej: Marco A2 16x22)")

                # --- SELECCIÓN DE SUCURSAL PARA INVENTARIO (ADMIN) ---
                elif boton_id == "btn_menu_inventarios":
                    enviar_mensaje_botones(numero_remitente, "📍 *Selector de Sucursal*\n¿Qué inventario deseas revisar?", [("btn_inv_scz", "Santa Cruz"), ("btn_inv_lpz", "La Paz"), ("btn_inv_cba", "Cochabamba")])

                elif boton_id.startswith("btn_inv_"):
                    sucursales_map = {"btn_inv_scz": "Santa Cruz", "btn_inv_lpz": "La Paz", "btn_inv_cba": "Cochabamba"}
                    sucursal_elegida = sucursales_map[boton_id]
                    enviar_texto(numero_remitente, f"⏳ Consultando inventario de {sucursal_elegida}...")
                    resultado = consultar_apps_script("consultar_inventario", sucursal=sucursal_elegida)
                    enviar_texto(numero_remitente, resultado)
                
                # --- CALENDARIO HISTORIAL ---
                elif boton_id == "btn_admin_trabajos":
                    fechas_menu = generar_fechas_recientes()
                    fechas_menu.insert(0, ("sumar_30", "📊 Sumar últimos 30 días"))
                    enviar_mensaje_lista(numero_remitente, "📅 Historial Diario", "Selecciona una opción:", "🗓️ Elegir", fechas_menu)

            # --- RESPUESTAS DE MENÚS DESPLEGABLES ---
            elif interaccion['type'] == 'list_reply':
                lista_id = interaccion['list_reply']['id']
                titulo_elegido = interaccion['list_reply']['title']
                
                if lista_id.startswith("sumar_"):
                    dias = int(lista_id.split("_")[1])
                    enviar_texto(numero_remitente, f"⏳ Sumando producción de los últimos {dias} días...\n\n_(Tip: Si deseas ver otro periodo, escríbeme 'Sumar 90' para 3 meses)_")
                    resultado = consultar_apps_script("sumar_historial", dias=dias)
                    enviar_texto(numero_remitente, resultado)

                elif lista_id.startswith("semana_"):
                    semana_atras = int(lista_id.split("_")[1])
                    enviar_texto(numero_remitente, f"⏳ Calculando producción de la semana seleccionada...")
                    resultado = consultar_apps_script("consultar_produccion_semanas", semana_offset=semana_atras)
                    enviar_texto(numero_remitente, resultado)

                elif lista_id.startswith("fecha_"):
                    fecha_elegida = lista_id.replace("fecha_", "")
                    enviar_texto(numero_remitente, f"⏳ Buscando registros del {fecha_elegida}...")
                    resultado = consultar_apps_script("consultar_trabajos", fecha=fecha_elegida)
                    enviar_texto(numero_remitente, resultado)

                elif lista_id.startswith("mod_"):
                    ESTADO_USUARIOS[numero_remitente] = {"modo": "esperando_numero", "item": titulo_elegido}
                    if rol_usuario == "admin":
                        enviar_texto(numero_remitente, f"Has seleccionado *{titulo_elegido}*.\n\nEscribe el *nuevo total faltante* que quieres fijar. (Ej: 15)")
                    elif rol_usuario == "carpintero":
                        enviar_texto(numero_remitente, f"Has seleccionado *{titulo_elegido}*.\n\nEscribe *cuántos cuadros terminaste hoy* para registrarlos. (Solo el número)")

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
