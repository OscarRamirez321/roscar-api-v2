from flask import Flask, request, jsonify, Response
from openai import OpenAI
from elevenlabs.client import ElevenLabs
import re
import os

app = Flask(__name__)

# Configura Flask para manejar UTF-8
app.config['JSON_AS_ASCII'] = False

# Configura las claves API desde variables de entorno
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Lista para almacenar citas y pedidos
citas = []
pedidos = []

# Lista de carros disponibles en Auto Source Network
car_inventory = [
    {"make": "BMW", "model": "X5", "year": 2020, "price": 38900, "mileage": 45000},
    {"make": "Mercedes-Benz", "model": "C-Class", "year": 2019, "price": 29900, "mileage": 52000},
    {"make": "Ford", "model": "F-150", "year": 2021, "price": 42900, "mileage": 38000},
    {"make": "Lexus", "model": "RX 350", "year": 2018, "price": 34900, "mileage": 60000},
]

# Contexto para Open AI
SYSTEM_MESSAGE = """
Eres Pedro, un asistente de ventas y atención al cliente para Auto Source Network, un dealership en Sarasota. Tu tono debe ser amigable, profesional y directo, como si estuvieras chateando con un cliente. Responde en mensajes cortos y naturales, como lo haría un humano. No uses emojis a menos que el cliente lo haga primero.

Ofrece información sobre los carros disponibles, financiamiento, y test drives. Aquí está el inventario de carros:
- BMW X5 2020 por $38900 (45000 millas)
- Mercedes-Benz C-Class 2019 por $29900 (52000 millas)
- Ford F-150 2021 por $42900 (38000 millas)
- Lexus RX 350 2018 por $34900 (60000 millas)

Si el cliente pregunta por un carro específico, dale los detalles y ofrécele un test drive. Si pregunta por financiamiento, menciona que Auto Source Network ofrece opciones para buen crédito, mal crédito o sin crédito. Si quiere un test drive, ofrécete a agendar uno y menciona que estás en Sarasota, abierto de lunes a sábado. Si no entiendes el mensaje, pide aclaraciones o sugiere opciones como buscar un carro, financiamiento o test drive.

También puedes agendar citas para test drives (por ejemplo, "Quiero una cita para el viernes a las 10") y registrar pedidos de carros (por ejemplo, "Quiero un BMW X5").
"""

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
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": pregunta}
            ],
            max_tokens=100,  # Limitamos para mantener las respuestas cortas
            temperature=0.7,
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

    # Escribe el audio en un archivo (opcional, para depuración)
    audio_path = "respuesta.mp3"
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    # Devuelve el audio como parte de la respuesta
    return Response(
        audio_bytes,
        mimetype="audio/mpeg",
        headers={"Content-Disposition": "attachment;filename=respuesta.mp3", "X-Text-Response": respuesta}
    )

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
