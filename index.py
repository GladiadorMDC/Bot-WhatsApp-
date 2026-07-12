from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# --- CREDENCIALES ---
VERIFY_TOKEN = "mi_token_secreto_carpinteria"
WHATSAPP_TOKEN = "EAAS11GIEA50BRvJRK4ZBCedOYRy8dfLlEgYc3GoZCT7nigtxPuy7ED5SR5oEAQOSIjgIKEjIgx414CifjihwE8ZBMtHNzfZBwo4Kawmd5GGTxbIuRNXVyZBvbQ0awinCpeCEQ72rALsuLMOpsYhFzQApYXQZC8K9HXsSETxMcQA4hks3654DbdmkHjUGbeMOJZAUQZDZD"
PHONE_NUMBER_ID = "1253318837856388"

# --- DICCIONARIO DE PERFILES ---
PERFILES = {
    "59178150540": "admin",             
    "591XXXXXXXX": "carpintero",        
    "591YYYYYYYY": "sucursal_lpz",      
    "591ZZZZZZZZ": "sucursal_cbba"      
}

def enviar_mensaje_botones(numero_destino, texto_body, botones_config):
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    botones_formateados = [{"type": "reply", "reply": {"id": b_id, "title": b_title}} for b_id, b_title in botones_config]
    data = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": texto_body},
            "action": {"buttons": botones_formateados}
        }
    }
    respuesta = requests.post(url, headers=headers, json=data)
    print(f"🤖 Meta responde a botones: {respuesta.json()}")

def enviar_texto(numero_destino, texto):
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": texto}
    }
    respuesta = requests.post(url, headers=headers, json=data)
    print(f"🤖 Meta responde a texto: {respuesta.json()}")

@app.route('/webhook', methods=['GET'])
def verificar_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode and token and mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge, 200
    return 'Bot activo', 200

@app.route('/webhook', methods=['POST'])
def recibir_mensajes():
    body = request.get_json()

    if body.get('object') and body.get('entry') and body['entry'][0].get('changes') and body['entry'][0]['changes'][0].get('value').get('messages'):
        mensaje_info = body['entry'][0]['changes'][0]['value']['messages'][0]
        numero_remitente = mensaje_info['from']
        
        print(f"📥 Mensaje recibido del número: {numero_remitente}")
        
        rol_usuario = PERFILES.get(numero_remitente, "desconocido")
        print(f"🕵️ Rol asignado en sistema: {rol_usuario}")

        if rol_usuario == "desconocido":
            enviar_texto(numero_remitente, "⛔ Acceso denegado. Este número no está registrado en el sistema del taller.")
            return jsonify({"status": "ok"}), 200

        # --- MENSAJE INICIAL ---
        if mensaje_info['type'] == 'text':
            print("📝 Es un mensaje de texto. Procesando menú inicial...")
            if rol_usuario == "admin":
                texto = "👑 *Panel de Administración*\nHola. Selecciona la acción a realizar:"
                botones = [("btn_admin_control", "⚙️ Control"), ("btn_admin_trabajos", "📋 Trabajos"), ("btn_admin_inv", "📊 Inventario")]
                enviar_mensaje_botones(numero_remitente, texto, botones)
            
            elif rol_usuario == "carpintero":
                texto = "🛠️ *Panel de Taller*\nHola Maestro. Seleccione una opción:"
                botones = [("btn_carp_lista", "📝 Lista Semanal"), ("btn_carp_inv", "🪵 Ver Inventario")]
                enviar_mensaje_botones(numero_remitente, texto, botones)

        # --- INTERACCIONES BOTONES ---
        elif mensaje_info['type'] == 'interactive':
            boton_id = mensaje_info['interactive']['button_reply']['id']
            print(f"👆 Botón presionado: {boton_id}")
            
            if rol_usuario == "admin":
                if boton_id == "btn_admin_control":
                    texto = "⚙️ *Control de Listas*\n¿Qué área deseas gestionar?"
                    botones = [("btn_ctrl_carpinteria", "🪵 L. Carpintería"), ("btn_ctrl_envios", "🚚 L. Envíos")]
                    enviar_mensaje_botones(numero_remitente, texto, botones)
                
                elif boton_id == "btn_ctrl_carpinteria":
                    texto = "🪵 *Lista de Carpintería Semanal*\nNo hay una lista activa."
                    botones = [("btn_crear_lista_carp", "✨ Crear Lista Nueva")]
                    enviar_mensaje_botones(numero_remitente, texto, botones)
                
                elif boton_id == "btn_ctrl_envios":
                    texto = "🚚 *Control de Envíos*\n¿Para qué sucursal generarás la lista?"
                    botones = [("btn_crear_envio_lpz", "📍 La Paz"), ("btn_crear_envio_cbba", "📍 Cochabamba")]
                    enviar_mensaje_botones(numero_remitente, texto, botones)
                
                elif boton_id == "btn_crear_lista_carp":
                    enviar_texto(numero_remitente, "⏳ Calculando necesidades de producción en base a ventas e inventario actual...")
                elif boton_id == "btn_crear_envio_lpz":
                    enviar_texto(numero_remitente, "⏳ Analizando inventario de Santa Cruz y necesidades de La Paz...")
                elif boton_id == "btn_crear_envio_cbba":
                    enviar_texto(numero_remitente, "⏳ Analizando inventario de Santa Cruz y necesidades de Cochabamba...")
                elif boton_id == "btn_admin_trabajos":
                    enviar_texto(numero_remitente, "📅 *Historial de Trabajos*\nEscribe la fecha que deseas consultar:")
                elif boton_id == "btn_admin_inv":
                    enviar_texto(numero_remitente, "📊 Mostrando inventario global...")

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
