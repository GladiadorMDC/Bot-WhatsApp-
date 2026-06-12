from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Este token lo pondrás en Meta más adelante
VERIFY_TOKEN = "mi_token_secreto_carpinteria" 

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
            
            # 1. SI EL USUARIO ESCRIBE UN TEXTO (Ej: "Hola")
            if mensaje_info['type'] == 'text':
                texto = mensaje_info['text']['body'].lower()
                print(f"Mensaje: {texto}")
                # Aquí enviaremos el Menú Principal con 3 botones:
                # - Añadir a inventario
                # - Enviar a sucursal
                # - Consultar inventario
                
            # 2. SI EL USUARIO TOCA UN BOTÓN
            elif mensaje_info['type'] == 'interactive':
                boton_id = mensaje_info['interactive']['button_reply']['id']
                
                # --- SUBMENÚ: AÑADIR A INVENTARIO ---
                if boton_id == "btn_añadir_inv":
                    # Aquí enviaremos 3 botones nuevos:
                    # 1. Seleccionar modelo (id: btn_seleccionar_modelo)
                    # 2. Añadidos hoy (id: btn_añadidos_hoy)
                    # 3. Stock del día (id: btn_stock_dia)
                    print("El usuario quiere añadir al inventario. Mostrando sub-opciones...")

                # --- SUBMENÚ: CONSULTAR INVENTARIO ---
                elif boton_id == "btn_consultar_inv":
                    # Aquí enviaremos 3 botones nuevos de sucursales:
                    # 1. La Paz (id: btn_suc_lapaz)
                    # 2. Santa Cruz (id: btn_suc_santacruz)
                    # 3. Cochabamba (id: btn_suc_cocha)
                    print("El usuario quiere consultar inventario. Mostrando sucursales...")
                
                # --- ACCIÓN: OBTENER EL STOCK DEL DÍA ---
                elif boton_id == "btn_stock_dia":
                    print("Calculando el algoritmo de producción diaria...")
                    # Aquí haremos la petición a Google Apps Script para ejecutar tu función matemática

        return jsonify({"status": "ok"}), 200
    return 'Not Found', 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
