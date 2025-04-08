from flask import Flask, request, jsonify
from openai import OpenAI
from elevenlabs.client import ElevenLabs
import re
import os

app = Flask(__name__)

# Configura Flask para manejar UTF-8
app.config['JSON_AS_ASCII'] = False

# Configura las claves API
openai_client = OpenAI(api_key="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")
elevenlabs_client = ElevenLabs(api_key="sk_51f0de7e4b1c883ac49899de828b5e314c15f8b95b494d1f")

# Lista para almacenar citas y pedidos
citas = []
pedidos = []

@app.route('/chat', methods=['POST'])
def chat():
    # Asegúrate de que el mensaje esté decodificado como UTF-8
    pregunta = request.json['message']

    # Detectar si el usuario quiere agendar una cita
    if "cita" in pregunta.lower() or "agendar" in pregunta.lower():
        match = re.search(r"(lunes|martes|miércoles|jueves|viernes|sábado|domingo) a las (\d{1,2})", pregunta.lower())
        if match:
            dia, hora = match.groups()
            cita = f"Cita agendada para el {dia} a las {hora}:00."
            citas.append(cita)
            respuesta = cita
        else:
            respuesta = "Por favor, dime el día y la hora para agendar tu cita. Por ejemplo: 'Quiero una cita para el viernes a las 10'."
    # Detectar si el usuario quiere hacer un pedido
    elif "pedido" in pregunta.lower() or "quiero un" in pregunta.lower():
        pedidos.append(pregunta)
        respuesta = f"Pedido registrado: {pregunta}. Te contactaremos para confirmar los detalles."
    else:
        # Respuesta de la API de OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres Roscar, un asistente de atención al cliente de Moto Express Solutions, un taller de motos. Eres experto en motos, muy amable y profesional. Puedes responder preguntas sobre servicios, precios, motos en stock, y ayudar a agendar citas o tomar pedidos."},
                {"role": "user", "content": pregunta}
            ]
        )
        respuesta = response.choices[0].message.content

    # Genera el audio de la respuesta
    audio_generator = elevenlabs_client.generate(
        text=respuesta,
        voice="Adam",
        model="eleven_multilingual_v2",
        voice_settings={
            "stability": 0.5,
            "similarity_boost": 0.8
        }
    )
    # Concatena los fragmentos del generador en un solo objeto bytes
    audio_bytes = b"".join(audio_generator)

    # Escribe el audio en un archivo
    audio_path = "respuesta.mp3"
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    # Devuelve la respuesta en UTF-8
    return jsonify({"respuesta": respuesta, "audio": audio_path})

if __name__ == '__main__':
    app.run(debug=True, port=5000)