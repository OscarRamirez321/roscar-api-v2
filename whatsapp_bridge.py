from flask import Flask, request, Response, send_from_directory
import requests
from twilio.twiml.messaging_response import MessagingResponse
import os

app = Flask(__name__)

# URL de tu API en Render
API_URL = "https://roscar-api-v2.onrender.com/chat"
NGROK_URL = "https://2de0-54-71-194-154.ngrok-free.app"  # Reemplaza con tu URL de ngrok

# Ruta para servir archivos estáticos (como respuesta.mp3)
@app.route('/<path:filename>')
def serve_static(filename):
    print(f"Sirviendo archivo: {filename}")
    return send_from_directory('.', filename)

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    # Obtener el mensaje de WhatsApp
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')  # Número del cliente
    print(f"Mensaje recibido de {from_number}: {incoming_msg}")

    # Enviar el mensaje a tu API
    payload = {"message": incoming_msg}
    headers = {"Content-Type": "application/json"}
    print(f"Enviando solicitud a {API_URL} con payload: {payload}")
    response = requests.post(API_URL, json=payload, headers=headers)
    print(f"Respuesta de la API: status_code={response.status_code}")

    if response.status_code == 200:
        # Obtener el texto de la respuesta
        text_response = response.headers.get('X-Text-Response', 'No se pudo obtener la respuesta.')
        print(f"Texto de la respuesta: {text_response}")

        # Crear la respuesta de Twilio
        twilio_response = MessagingResponse()
        msg = twilio_response.message()
        msg.body(text_response)  # Enviar solo el texto
        print(f"Enviando respuesta a WhatsApp: texto={text_response}")

        return str(twilio_response)
    else:
        print(f"Error al contactar la API: {response.status_code} - {response.text}")
        twilio_response = MessagingResponse()
        msg = twilio_response.message()
        msg.body("Lo siento, hubo un error al procesar tu mensaje. Intenta de nuevo.")
        return str(twilio_response)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)