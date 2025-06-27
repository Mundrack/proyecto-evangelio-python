# archivo: database.py
# Propósito: Gestionar la conexión centralizada a la base de datos MongoDB.
# Este módulo se encarga de inicializar el cliente de MongoDB y proporcionar
# una función para acceder a la instancia de la base de datos desde cualquier
# parte de la aplicación.

# --- 1. IMPORTACIONES ---
import os                    # Para acceder a las variables de entorno.
from pymongo import MongoClient # El driver oficial de MongoDB para Python.
from pymongo.errors import ConnectionFailure # Para capturar errores de conexión.
from dotenv import load_dotenv # Para cargar las variables del archivo .env.

# --- 2. CONFIGURACIÓN INICIAL ---

# Carga las variables definidas en el archivo .env en el entorno del sistema.
# Esto hace que os.getenv() pueda encontrarlas.
load_dotenv()

# Lee la cadena de conexión y el nombre de la base de datos desde las variables de entorno.
# Usar .env mantiene las credenciales seguras y fuera del código fuente.
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = "Proyecto_Integrador"  # El nombre de tu base de datos en MongoDB Atlas.

# Declaramos las variables `client` y `db_instance` globalmente.
# `client` mantendrá la conexión persistente con el servidor de MongoDB.
# `db_instance` guardará la referencia a nuestra base de datos específica para no tener que buscarla cada vez.
client = None
db_instance = None

# --- 3. INICIALIZACIÓN DE LA CONEXIÓN ---

# Este bloque intenta establecer la conexión tan pronto como se importa el módulo.
# Si falla aquí, la aplicación no podrá continuar, lo cual es un comportamiento deseado.
try:
    # Verificamos que MONGO_URI se haya cargado correctamente.
    if not MONGO_URI:
        raise ValueError("La variable de entorno MONGO_URI no está definida. Revisa tu archivo .env.")
    
    print("INFO: Intentando establecer conexión con MongoDB Atlas...")
    # Creamos una instancia del cliente de MongoDB.
    # `serverSelectionTimeoutMS` define cuánto tiempo (en ms) esperará el driver
    # para encontrar un servidor disponible antes de lanzar un error. 5 segundos es un valor razonable.
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    
    # El "ping" es la forma recomendada de verificar si la conexión es exitosa.
    # Lanza una excepción (ConnectionFailure) si no se puede conectar.
    client.admin.command('ping')
    
    print("SUCCESS: ¡Conexión a MongoDB Atlas establecida y verificada exitosamente!")
    
except ConnectionFailure as e:
    # Si el ping falla, la conexión no es válida (ej: IP no en whitelist, contraseña incorrecta).
    print(f"FATAL: No se pudo conectar a MongoDB. Error de conexión: {e}")
    client = None
except ValueError as e:
    # Si la variable de entorno no está definida.
    print(f"FATAL: Error de configuración. {e}")
    client = None
except Exception as e:
    # Captura cualquier otro error inesperado durante la inicialización.
    print(f"FATAL: Ocurrió un error inesperado al conectar a la base de datos: {e}")
    client = None

# --- 4. FUNCIÓN DE ACCESO A LA BASE DE DATOS ---

def get_db():
    """
    Función principal para obtener la instancia de la base de datos.

    Esta función utiliza las variables globales `client` y `db_instance` para
    proporcionar un acceso eficiente a la base de datos. Si la instancia ya
    ha sido creada, la retorna inmediatamente (patrón Singleton).

    Returns:
        Db: La instancia de la base de datos de MongoDB si la conexión es exitosa.
        None: Si el cliente no pudo ser inicializado.
    """
    global db_instance
    
    # Si el cliente no se pudo inicializar en el paso anterior, no hay nada que hacer.
    if client is None:
        print("ERROR: Se solicitó la base de datos, pero el cliente de MongoDB no está inicializado.")
        return None
        
    # Si la instancia de la base de datos ya fue obtenida antes, la reutilizamos.
    # Esto es más eficiente que acceder a `client[DB_NAME]` en cada llamada.
    if db_instance is None:
        print("INFO: Obteniendo instancia de la base de datos por primera vez.")
        db_instance = client[DB_NAME]
        
    return db_instance