from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# --- CREDENCIALES ---
VERIFY_TOKEN = "mi_token_secreto_carpinteria"
WHATSAPP_TOKEN = "EAAS11GIEA50BRvJRK4ZBCedOYRy8dfLlEgYc3GoZCT7nigtxPuy7ED5SR5oEAQOSIjgIKEjIgx414CifjihwE8ZBMtHNzfZBwo4Kawmd5GGTxbIuRNXVyZBvbQ0awinCpeCEQ72rALsuLMOpsYhFzQApYXQZC8K9HXsSETxMcQA4hks3654DbdmkHjUGbeMOJZAUQZDZD"
PHONE_NUMBER_ID = "1253318837856388"

def enviar_mensaje_botones(numero_destino, texto_body, botones_config):
    """Función maestra para enviar cualquier mensaje con botones"""
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    botones_formateados = []
    for btn_id, btn_title in botones_config:
        botones_formateados.append({
            "type": "reply",
            "reply": {
                "id": btn_id,
                "title": btn_title
            }
        })

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
    requests.post(url, headers=headers, json=data)

def enviar_texto(numero_destino, texto):
    """Función para enviar texto simple"""
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
    requests.post(url, headers=headers, json=data)

@app.route('/webhook', methods=['GET'])
def verificar_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return 'Prohibido', 403
    return 'Bot activo', 200

@app.route('/webhook', methods=['POST'])
def recibir_mensajes():
    body = request.get_json()

    if body.get('object'):
        if body.get('entry') and body['entry'][0].get('changes') and body['entry'][0]['changes'][0].get('value').get('messages'):
            mensaje_info = body['entry'][0]['changes'][0]['value']['messages'][0]
            numero_remitente = mensaje_info['from']
            
            # --- MENSAJE DE TEXTO (Menú Principal) ---
            if mensaje_info['type'] == 'text':
                texto_menu = "🪵 *Sistema de Inventario*\n\nHola. Selecciona la acción que deseas realizar hoy:"
                botones_menu = [
                    ("btn_añadir_inv", "📥 Añadir a inv."),
                    ("btn_enviar_sucursal", "🚚 Enviar sucursal"),
                    ("btn_consultar_inv", "📊 Consultar inv.")
                ]
                enviar_mensaje_botones(numero_remitente, texto_menu, botones_menu)
                
            # --- INTERACCIONES CON BOTONES ---
            elif mensaje_info['type'] == 'interactive':
                boton_id = mensaje_info['interactive']['button_reply']['id']
                
                # Opciones del menú principal
                if boton_id == "btn_añadir_inv":
                    texto = "⚙️ *Opciones de Producción e Inventario*:\n¿Qué deseas registrar o consultar?"
                    botones = [
                        ("btn_seleccionar_modelo", "🖼️ Seleccionar modelo"),
                        ("btn_añadidos_hoy", "📅 Añadidos hoy"),
                        ("btn_stock_dia", "⚡ Stock del día")
                    ]
                    enviar_mensaje_botones(numero_remitente, texto, botones)
                    
                elif boton_id in ["btn_enviar_sucursal", "btn_consultar_inv"]:
                    texto = "📍 *Selecciona la sucursal*:"
                    botones = [
                        ("btn_suc_santacruz", "Santa Cruz"),
                        ("btn_suc_lapaz", "La Paz"),
                        ("btn_suc_cochabamba", "Cochabamba")
                    ]
                    enviar_mensaje_botones(numero_remitente, texto, botones)

                # Acciones finales (Aquí es donde conectaremos con Google Drive)
                elif boton_id == "btn_seleccionar_modelo":
                    enviar_texto(numero_remitente, "🔜 Aquí se desplegará la lista interactiva con los modelos de marcos.")
                elif boton_id == "btn_stock_dia":
                    enviar_texto(numero_remitente, "🧮 Calculando algoritmo de producción... (Conectando a base de datos)")
                else:
                    enviar_texto(numero_remitente, f"Recibido. Opción seleccionada lista para programar lógica.")

        return jsonify({"status": "ok"}), 200
    return 'Not Found', 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
