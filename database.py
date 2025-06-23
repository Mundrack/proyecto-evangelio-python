# archivo: database.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DB_NAME')

# Creamos una única instancia del cliente para ser reutilizada
client = MongoClient(MONGO_URI)

def get_db():
    """
    Función para obtener la instancia de la base de datos.
    Reutiliza la conexión del cliente.
    """
    try:
        # Ping al servidor para verificar la conexión
        client.admin.command('ping')
        # print("Conexión a MongoDB exitosa.")
        db = client[DB_NAME]
        return db
    except Exception as e:
        print(f"No se pudo conectar a MongoDB: {e}")
        return None