# archivo: database.py
# Propósito: Gestionar la conexión a la base de datos MongoDB.

import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = "Proyecto_Integrador" 

client = None
db_instance = None

try:
    print("Estableciendo cliente de MongoDB...")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
except Exception as e:
    print(f"ERROR: No se pudo crear el cliente de MongoDB. Detalle: {e}")
    client = None

def get_db():
    global db_instance
    if db_instance is not None:
        return db_instance
    
    if client is None:
        print("ERROR: El cliente de MongoDB no está inicializado.")
        return None

    try:
        client.admin.command('ping')
        print("¡Ping a MongoDB Atlas exitoso!")
        db_instance = client[DB_NAME]
        return db_instance
    except Exception as e:
        print(f"ERROR: No se pudo conectar a MongoDB o hacer ping. Detalle: {e}")
        db_instance = None 
        return None