# ==============================================================================
# soluIA v2.6 - Asesor de Ventas Multicanal (Web + WhatsApp)
# Arquitectura: Máquina de Estados Finitos (FSM) con Clases
# Desarrollado por: Oscar Ramirez (CEO) y Gemini (CTO)
# ==============================================================================

# --- 1. IMPORTACIÓN DE LIBRERÍAS Y HERRAMIENTAS ---
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, render_template, make_response
from openai import OpenAI
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from twilio.twiml.messaging_response import MessagingResponse

# --- 2. CONFIGURACIÓN INICIAL ---
load_dotenv()
app = Flask(__name__, template_folder='templates')
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

# "Base de datos" de sesiones en memoria. Clave: session_id, Valor: instancia de ConversacionManager
user_sessions = {}

print("✅ Servidor soluIA v2.6 (Multicanal) iniciado.")

# --- 3. FUNCIONES DE APOYO ---

def get_sheet():
    """Se conecta de forma segura a Google Sheets."""
    try:
        scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        client = gspread.authorize(creds)
        return client.open("Inventario Rodrigo").sheet1
    except Exception as e:
        print(f"❌ Error crítico al conectar con Google Sheets: {e}")
        return None

def buscar_productos_por_termino(sheet, termino_busqueda):
    """
    LÓGICA DE BÚSQUEDA AVANZADA (Inspirada en tu versión):
    Busca productos que contengan palabras clave de la frase del usuario.
    """
    if not sheet or not termino_busqueda: return []
    try:
        resultados = []
        list_of_rows = sheet.get_all_values()
        
        stopwords = {"y","o","de","la","el","en","un","una","quisiera","quiero"}
        palabras_usuario = set(re.findall(r'\b\w+\b', termino_busqueda.lower()))
        palabras_clave = palabras_usuario - stopwords

        print(f"🕵️  Palabras clave para buscar: {palabras_clave}")

        for row in list_of_rows[1:]:
            if len(row) < 3: continue
            nombre_producto_lower = row[0].lower()
            try:
                stock = int(row[1])
            except (ValueError, IndexError):
                stock = 0

            if stock > 0 and any(clave in nombre_producto_lower for clave in palabras_clave):
                resultados.append({"nombre": row[0], "stock": stock, "precio": float(row[2])})
        
        print(f"📦 Búsqueda finalizada. Se encontraron {len(resultados)} productos.")
        return resultados
    except Exception as e:
        print(f"❌ Error al buscar productos: {e}")
        return []

def enviar_email_pedido(datos):
    """Función completa y robusta para enviar notificación de pedido por email."""
    if not all([EMAIL_ADDRESS, EMAIL_PASSWORD, EMAIL_RECEIVER]):
        print("⚠️  Credenciales de email no configuradas en .env.")
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = f"soluIA Bot <{EMAIL_ADDRESS}>"
        msg["To"] = EMAIL_RECEIVER
        msg["Subject"] = f"Nuevo pedido de {datos.get('nombre')}"
        
        total = sum(item['precio'] * item.get('cantidad', 1) for item in datos.get('carrito', []))
        
        texto = f"Cliente: {datos.get('nombre')}\nTel: {datos.get('telefono')}\nDir: {datos.get('direccion')}\nRef: {datos.get('referencia')}\nCédula: {datos.get('cedula')}\nPago: {datos.get('metodo_pago')}\n\nProductos:\n"
        for item in datos.get('carrito', []):
            subtotal = item['precio'] * item.get('cantidad', 1)
            texto += f"- {item.get('cantidad', 1)} x {item.get('nombre', 'N/A')} = C${subtotal:.2f}\n"
        texto += f"\nTotal: C${total:.2f}"
        
        msg.attach(MIMEText(texto, "plain"))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Email enviado con éxito.")
        return True
    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        return False

# --- 4. LA MÁQUINA DE ESTADOS (FSM) ---

class ConversacionManager:
    """Maneja el estado y la lógica de la conversación para un único usuario."""
    def __init__(self, session_id):
        session_data = user_sessions.get(session_id, {"estado": "inicio", "datos_recolectados": {"carrito": []}})
        self.session_id = session_id
        self.estado = session_data["estado"]
        self.datos = session_data["datos_recolectados"]

    def guardar_estado(self):
        user_sessions[self.session_id] = {"estado": self.estado, "datos_recolectados": self.datos}

    def siguiente_paso(self, msg):
        texto = msg.strip().lower()
        
        # Intenciones generales que pueden reiniciar o dar info rápida
        if re.search(r'\b(hola|buenas|hey)\b', texto):
            return "¡Hola! Soy Rodrigo, tu asistente virtual. ¿Qué producto buscas hoy?"
        if re.search(r'\b(gracias|adiós|chao|bye)\b', texto):
            user_sessions.pop(self.session_id, None)
            return "¡Un gusto atenderte! Si necesitas algo más, aquí estoy. 😊"
        if re.search(r'\b(dónde|ubicación|dirección)\b', texto):
            return "📍 Estamos en Km 14 Carretera a Masaya, Managua."
        
        sheet = get_sheet()
        if not sheet: return "Lo siento, el sistema de inventario no está disponible."

        # Flujo por Estados
        if self.estado == "esperando_seleccion_producto":
            try:
                opts = self.datos["opciones_listadas"]
                idx = int(texto) - 1
                if 0 <= idx < len(opts):
                    prod = opts[idx]
                    self.datos["producto_temp"] = prod
                    self.estado = "esperando_cantidad"
                    return f"✅ Seleccionado '{prod['nombre']}'. ¿Cuántas unidades deseas cotizar?"
                else:
                    return "Ese número no está en la lista. Intenta de nuevo."
            except ValueError:
                return self.procesar_busqueda(msg, sheet)

        elif self.estado == "esperando_cantidad":
            m = re.search(r'\d+', texto)
            if not m: return "Por favor indica la cantidad en números."
            
            cant = int(m.group())
            prod = self.datos["producto_temp"]
            if cant > prod["stock"]: return f"Solo hay {prod['stock']} unidades."
            
            self.datos["carrito"].append({**prod, "cantidad": cant})
            self.estado = "menu_post_agregado"
            return f"✅ Agregado. Tienes {len(self.datos['carrito'])} ítems.\n¿Deseas añadir otro producto o finalizar?"

        elif self.estado == "menu_post_agregado":
            if "otro" in texto:
                self.estado = "inicio"
                return "¿Qué otro producto buscas?"
            if "finalizar" in texto or "comprar" in texto:
                self.estado = "esperando_nombre"
                return "Perfecto, dime tu nombre completo."
            return "¿Deseas otro producto o finalizar?"

        # (El resto del flujo de recolección de datos que diseñaste, integrado aquí)
        elif self.estado == "esperando_nombre":
            self.datos["nombre"] = msg.title().strip()
            self.estado = "esperando_telefono"
            return f"¡Gracias {self.datos['nombre']}! ¿Tu teléfono?"
        
        elif self.estado == "esperando_telefono":
            num = re.sub(r'\D', '', msg)
            if len(num) < 7: return "Teléfono inválido, intenta de nuevo."
            self.datos["telefono"] = num
            self.estado = "esperando_direccion"
            return "¿Dirección de entrega?"
            
        elif self.estado == "esperando_direccion":
            self.datos["direccion"] = msg.strip()
            self.estado = "esperando_referencia"
            return "¿Punto de referencia?"
            
        elif self.estado == "esperando_referencia":
            self.datos["referencia"] = msg.strip()
            self.estado = "esperando_cedula"
            return "¿Número de cédula para factura?"
            
        elif self.estado == "esperando_cedula":
            ced = msg.strip()
            if not re.fullmatch(r'[0-9A-Za-z]{5,15}', ced): return "Cédula inválida."
            self.datos["cedula"] = ced
            self.estado = "esperando_metodo_pago"
            return "Elige método de pago: Efectivo o Transferencia."
            
        elif self.estado == "esperando_metodo_pago":
            self.datos["metodo_pago"] = msg.strip().title()
            enviar_email_pedido(self.datos)
            resumen = "✅ Pedido registrado. Te contactaremos pronto. ¡Gracias!"
            # Reiniciar para la próxima conversación
            self.estado = "inicio"
            self.datos = {"carrito": []}
            return resumen
        
        # Estado inicial
        else:
            return self.procesar_busqueda(texto, sheet)

    def procesar_busqueda(self, msg, sheet):
        encontrados = buscar_productos_por_termino(sheet, msg)
        if not encontrados: return "No hallé productos con ese nombre. ¿Pruebas otro término?"
        
        if len(encontrados) == 1:
            p = encontrados[0]
            self.datos["producto_temp"] = p
            self.estado = "esperando_cantidad"
            return f"✅ Encontré '{p['nombre']}' a C${p['precio']:.2f}. ¿Cuántas unidades deseas cotizar?"
        
        self.datos["opciones_listadas"] = encontrados
        self.estado = "esperando_seleccion_producto"
        texto = "He encontrado:\n" + "\n".join([f"{i+1}. {p['nombre']} – C${p['precio']:.2f}" for i,p in enumerate(encontrados)])
        texto += "\n\nElige el número del producto que te interesa."
        return texto

# --- 5. ENDPOINTS ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route("/chat_web", methods=['POST'])
def chat_web():
    session_id = request.json.get('session_id', 'web_user')
    msg = request.json.get('message', '')
    
    # Cada usuario tiene su propia conversación
    if session_id not in user_sessions:
        user_sessions[session_id] = {}
        
    manager = ConversacionManager(session_id)
    resp = manager.siguiente_paso(msg)
    manager.guardar_estado()
    
    return jsonify({'reply': resp})

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    from_num = request.values.get('From', '')
    body = request.values.get('Body', '')
    
    if from_num not in user_sessions:
        user_sessions[from_num] = {}
        
    manager = ConversacionManager(from_num)
    resp = manager.siguiente_paso(body)
    manager.guardar_estado()
    
    twresp = MessagingResponse()
    twresp.message(resp)
    return make_response(str(twresp), 200)

if __name__ == "__main__":
    app.run(debug=True, port=5001)