# archivo: crear_usuario.py (VERSIÓN CORREGIDA)

from werkzeug.security import generate_password_hash # Asegúrate que esta importación está
from database import get_db

def crear_o_actualizar_usuario():
    """
    Un script de utilidad para crear o actualizar usuarios en la base de datos
    con contraseñas hasheadas correctamente.
    """
    
    # --- DATOS DEL USUARIO QUE QUIERES CREAR/ACTUALIZAR ---
    
    # Cambia estos valores para cada usuario que quieras gestionar
    nombre_usuario = "crivera"
    contrasena_plana = "user123"
    rol_usuario = "catequizando"
    nombre_completo = "Camila Rivera La preciosa"
    cedula = "1724864985" # ¡Importante añadir la cédula aquí!

    # --- LÓGICA DEL SCRIPT ---
    
    # Hasheamos la contraseña USANDO EL MÉTODO POR DEFECTO Y RECOMENDADO
    hash_contrasena = generate_password_hash(contrasena_plana)
    
    print(f"Usuario: {nombre_usuario}")
    print(f"Contraseña en texto plano: {contrasena_plana}")
    print(f"Hash generado: {hash_contrasena}\n")
    
    db = get_db()
    
    if db is None:
        print("Error: No se pudo conectar a la base de datos.")
        return

    usuarios_collection = db.usuarios
    
    filtro = {'usuario': nombre_usuario}
    
    actualizacion = {
        '$set': {
            'contrasena': hash_contrasena,
            'rol': rol_usuario,
            'nombre_completo': nombre_completo
        }
    }
    if cedula:
        actualizacion['$set']['cedula_asociada'] = cedula

    resultado = usuarios_collection.update_one(filtro, actualizacion, upsert=True)
    
    if resultado.matched_count > 0:
        print(f"¡Usuario '{nombre_usuario}' actualizado exitosamente!")
    elif resultado.upserted_id:
        print(f"¡Usuario '{nombre_usuario}' creado exitosamente con ID: {resultado.upserted_id}!")
    else:
        print("No se realizaron cambios.")

if __name__ == '__main__':
    print("--- Iniciando script para gestionar usuarios ---")
    crear_o_actualizar_usuario()
    print("--- Script finalizado ---")