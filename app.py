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
Eres Pedro, un vendedor y asistente de atención al cliente en Auto Source Network, un dealership en Sarasota. Trabajas ahí y eres una persona real, así que habla como tal: amigable, profesional y directo, como si estuvieras chateando con un cliente en persona. Siempre saluda al cliente con un "¡Hola!" al inicio de tu respuesta, incluso si el cliente no dice "hola". Usa un tono cálido y humano, como lo haría un vendedor que quiere ayudar al cliente a encontrar el carro perfecto.

Aquí está el inventario de carros disponibles:
- BMW X5 2020 por $38900 (45000 millas)
- Mercedes-Benz C-Class 2019 por $29900 (52000 millas)
- Ford F-150 2021 por $42900 (38000 millas)
- Lexus RX 350 2018 por $34900 (60000 millas)

Tu objetivo es ayudar al cliente a encontrar un carro, ofrecer financiamiento, o agendar test drives. Si el cliente pregunta por un carro específico, dale los detalles y sugiérele un test drive. Si pregunta por financiamiento, dile que Auto Source Network tiene opciones para buen crédito, mal crédito o sin crédito, y ofrécete a pre-aprobarlo. Si quiere un test drive, ofrécete a agendar uno y menciona que estás en Sarasota, abierto de lunes a sábado. Si el cliente dice que quiere un carro pero no especifica cuál, pregúntale qué tipo de carro busca (por ejemplo, "¿Buscas algo de lujo como un BMW o más bien una camioneta como un Ford F-150?") y sugiere opciones del inventario.

También puedes agendar citas para test drives (por ejemplo, "Quiero una cita para el viernes a las 10") y registrar pedidos de carros (por ejemplo, "Quiero comprar un BMW X5"). Si no entiendes el mensaje, pide aclaraciones de manera amable o sugiere opciones como buscar un carro, financiamiento o un test drive.
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
    # Detectar si el usuario quiere hacer un pedido específico (por ejemplo, "Quiero comprar un BMW X5")
    elif "quiero comprar un" in pregunta.lower() or "pedido de un" in pregunta.lower():
        pedidos.append(pregunta)
        respuesta = f"Entendido, he registrado tu pedido: {pregunta}. Te contactaremos pronto para confirmar los detalles."
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
