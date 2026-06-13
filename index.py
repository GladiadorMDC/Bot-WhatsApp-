from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# --- CREDENCIALES ---
VERIFY_TOKEN = "mi_token_secreto_carpinteria"
WHATSAPP_TOKEN = "EAAS11GIEA50BRvJRK4ZBCedOYRy8dfLlEgYc3GoZCT7nigtxPuy7ED5SR5oEAQOSIjgIKEjIgx414CifjihwE8ZBMtHNzfZBwo4Kawmd5GGTxbIuRNXVyZBvbQ0awinCpeCEQ72rALsuLMOpsYhFzQApYXQZC8K9HXsSETxMcQA4hks3654DbdmkHjUGbeMOJZAUQZDZD"
PHONE_NUMBER_ID = "1253318837856388"

def enviar_menu_principal(numero_destino):
    """Función para enviar el menú con 3 botones a través de la API de Meta"""
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Nota: Los títulos de los botones en WhatsApp tienen un límite estricto de 20 caracteres.
    data = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "🪵 *Sistema de Inventario*\n\nHola. Selecciona la acción que deseas realizar hoy:"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "btn_añadir_inv",
                            "title": "📥 Añadir a inv."
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "btn_enviar_sucursal",
                            "title": "🚚 Enviar sucursal"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "btn_consultar_inv",
                            "title": "📊 Consultar inv."
                        }
                    }
                ]
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    print("Respuesta de Meta:", response.json())

def enviar_texto(numero_destino, texto):
    """Función temporal para responder cuando tocan un botón"""
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
            
            # --- SI LLEGA UN MENSAJE DE TEXTO (Ej: "Hola") ---
            if mensaje_info['type'] == 'text':
                texto = mensaje_info['text']['body']
                print(f"Mensaje recibido: {texto}")
                # Disparamos el menú principal
                enviar_menu_principal(numero_remitente)
                
            # --- SI EL USUARIO TOCA UN BOTÓN ---
            elif mensaje_info['type'] == 'interactive':
                boton_id = mensaje_info['interactive']['button_reply']['id']
                
                if boton_id == "btn_añadir_inv":
                    enviar_texto(numero_remitente, "⏳ Procesando sub-menú de añadir marcos...")
                elif boton_id == "btn_enviar_sucursal":
                    enviar_texto(numero_remitente, "⏳ Procesando sub-menú de envíos...")
                elif boton_id == "btn_consultar_inv":
                    enviar_texto(numero_remitente, "⏳ Procesando consulta de stock...")

        return jsonify({"status": "ok"}), 200
    return 'Not Found', 404
    @app.route('/iniciar', methods=['GET'])
def forzar_primer_mensaje():
    """Ruta secreta para forzar el primer mensaje de Meta y abrir el chat"""
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # IMPORTANTE: Aquí pones tu número de Bolivia con el código de país (591)
    numero_bolivia = "591XXXXXXXX" 
    
    data = {
        "messaging_product": "whatsapp",
        "to": numero_bolivia,
        "type": "template",
        "template": {
            "name": "hello_world",
            "language": {"code": "en_US"}
        }
    }
    
    respuesta = requests.post(url, headers=headers, json=data)
    return f"¡Orden enviada a Meta! Resultado: {respuesta.text}"


if __name__ == '__main__':
    app.run(debug=True, port=5000)
