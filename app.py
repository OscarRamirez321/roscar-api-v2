from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# Lista de carros disponibles en Auto Source Network (para la demostración)
car_inventory = [
    {"make": "BMW", "model": "X5", "year": 2020, "price": 38900, "mileage": 45000},
    {"make": "Mercedes-Benz", "model": "C-Class", "year": 2019, "price": 29900, "mileage": 52000},
    {"make": "Ford", "model": "F-150", "year": 2021, "price": 42900, "mileage": 38000},
    {"make": "Lexus", "model": "RX 350", "year": 2018, "price": 34900, "mileage": 60000},
]

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    # Obtener el mensaje del cliente
    incoming_msg = request.values.get('Body', '').lower().strip()
    from_number = request.values.get('From', '')

    # Crear la respuesta de Twilio
    twilio_response = MessagingResponse()
    msg = twilio_response.message()

    # Presentación inicial de Pedro si el mensaje incluye "hola" o es el primer mensaje
    if "hola" in incoming_msg:
        response_text = "¡Hola! Soy Pedro, tu asistente en Auto Source Network aquí en Sarasota. 😊 ¿Buscas un carro o necesitas ayuda con algo?"
        msg.body(response_text)
        return str(twilio_response)

    # Responder a preguntas sobre el inventario
    if "carros" in incoming_msg or "inventario" in incoming_msg or "disponible" in incoming_msg:
        response_text = "Claro, tenemos varios carros disponibles. Aquí algunos:\n"
        for car in car_inventory[:3]:  # Mostrar solo 3 carros para mantener el mensaje corto
            response_text += f"- {car['make']} {car['model']} {car['year']} por ${car['price']} ({car['mileage']} millas)\n"
        response_text += "¿Te interesa alguno? Puedo darte más detalles."
        msg.body(response_text)
        return str(twilio_response)

    # Responder a preguntas sobre un carro específico (por ejemplo, "BMW" o "F-150")
    for car in car_inventory:
        if car['make'].lower() in incoming_msg or car['model'].lower() in incoming_msg:
            response_text = f"El {car['make']} {car['model']} {car['year']} que tenemos cuesta ${car['price']} y tiene {car['mileage']} millas. ¿Quieres venir a verlo o necesitas más info?"
            msg.body(response_text)
            return str(twilio_response)

    # Responder a preguntas sobre financiamiento
    if "financiamiento" in incoming_msg or "credito" in incoming_msg or "pago" in incoming_msg:
        response_text = "¡Claro! En Auto Source Network ofrecemos financiamiento, incluso si tienes buen crédito, mal crédito o no tienes crédito. ¿Te gustaría que te ayude a pre-aprobarte?"
        msg.body(response_text)
        return str(twilio_response)

    # Responder a preguntas sobre test drives
    if "test drive" in incoming_msg or "probar" in incoming_msg:
        response_text = "¡Genial! Podemos agendar un test drive. ¿Qué carro te gustaría probar? Estamos en Sarasota, abiertos de lunes a sábado."
        msg.body(response_text)
        return str(twilio_response)

    # Respuesta por defecto si no entiende el mensaje
    response_text = "No estoy seguro de cómo ayudarte con eso. ¿Buscas un carro, información sobre financiamiento o quieres agendar un test drive?"
    msg.body(response_text)
    return str(twilio_response)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)
