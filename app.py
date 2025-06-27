# archivo: app.py (VERSIÓN CORREGIDA Y MEJORADA)
# Propósito: El corazón de la aplicación web.

# --- 1. IMPORTACIONES ---
from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import get_db
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os # Buena práctica para manejar la secret key

# --- 2. CONFIGURACIÓN DE LA APLICACIÓN ---
app = Flask(__name__)
# ### CAMBIO CLAVE 1: Usar una variable de entorno para la secret key es más seguro.
# Si no la tienes, usará la que ya tenías.
app.secret_key = os.getenv('SECRET_KEY', 'un-secreto-muy-bien-guardado-para-el-proyecto')

# --- 3. DECORADOR DE AUTENTICACIÓN (LÓGICA SIMPLIFICADA Y CORREGIDA) ---
### CAMBIO CLAVE 2: Un decorador mucho más claro y robusto.
def login_required(roles_permitidos=None):
    if roles_permitidos is None:
        roles_permitidos = [] # Por defecto, solo requiere estar logueado.
        
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. ¿Hay alguien logueado?
            if 'user_id' not in session:
                flash("Debes iniciar sesión para acceder a esta página.", "warning")
                return redirect(url_for('login'))

            user_role = session.get('rol')
            
            # 2. ¿El rol 'admin' tiene acceso a todo? Sí.
            if user_role == 'admin':
                return f(*args, **kwargs)

            # 3. ¿La ruta no requiere un rol específico? (Solo estar logueado)
            if not roles_permitidos:
                return f(*args, **kwargs)

            # 4. ¿El rol del usuario está en la lista de roles permitidos?
            if user_role in roles_permitidos:
                return f(*args, **kwargs)
            
            # 5. Si nada de lo anterior se cumple, no tiene permisos.
            flash("No tienes los permisos necesarios para realizar esta acción.", "error")
            return redirect(url_for('index'))
        return decorated_function
    return decorator

# --- 4. RUTAS DE AUTENTICACIÓN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        db = get_db()
        if db is None:
            flash("Error crítico de conexión con la base de datos.", "error")
            return render_template('login.html')
        
        usuario_db = db.usuarios.find_one({'usuario': request.form['usuario']})
        
        if usuario_db and check_password_hash(usuario_db.get('contrasena', ''), request.form['contrasena']):
            session['user_id'] = str(usuario_db['_id'])
            session['usuario'] = usuario_db['usuario']
            session['rol'] = usuario_db['rol']
            # ### CAMBIO CLAVE 3: Guardamos también el nombre completo para mostrarlo. Es más amigable.
            session['nombre_completo'] = usuario_db.get('nombre_completo', usuario_db['usuario'])
            flash(f"¡Bienvenido de vuelta, {session['nombre_completo']}!", 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('login'))

@app.route('/registrar_usuario', methods=['GET', 'POST'])
@login_required(roles_permitidos=['admin']) # Solo los admins pueden acceder
def registrar_usuario():
    if request.method == 'POST':
        db = get_db()
        if db.usuarios.find_one({'usuario': request.form['usuario']}):
            flash(f"El nombre de usuario '{request.form['usuario']}' ya existe.", "error")
            return redirect(url_for('registrar_usuario'))
        
        nuevo_usuario = {
            'usuario': request.form['usuario'],
            'contrasena': generate_password_hash(request.form['contrasena']),
            'rol': request.form['rol'],
            'nombre_completo': request.form['nombre_completo']
        }
        
        # Si el rol es 'catequizando', intentamos asociarlo por la cédula
        cedula_asociada = request.form.get('cedula_asociada')
        if request.form['rol'] == 'catequizando' and cedula_asociada:
            # Primero, nos aseguramos que el catequizando exista
            catequizando = db.catequizandos.find_one({'datos_personales.cedula': cedula_asociada})
            if catequizando:
                nuevo_usuario['catequizando_id'] = catequizando['_id']
            else:
                flash(f"La Cédula '{cedula_asociada}' no fue encontrada en ningún catequizando. El usuario se creó sin asociación.", "warning")
        
        db.usuarios.insert_one(nuevo_usuario)
        flash(f"Usuario '{request.form['usuario']}' registrado con éxito.", "success")
        return redirect(url_for('index')) # Redirigir al inicio para ver la lista de usuarios (si la implementamos)

    return render_template('registrar_usuario.html')

@app.route('/')
@login_required()
def index():
    db = get_db()
    lista_catequizandos_final = []
    
    if db is None:
        flash("Error de conexión con la base de datos.", "error")
        return render_template('index.html', catequizandos=[])
    
    user_role = session.get('rol')
    user_id = ObjectId(session.get('user_id'))
    
    pipeline_base = [
        {
            "$lookup": {
                "from": "grupos",
                "localField": "grupo_id",
                "foreignField": "_id",
                "as": "grupo_info"
            }
        },
        {
            "$unwind": {
                "path": "$grupo_info",
                "preserveNullAndEmptyArrays": True
            }
        }
    ]

    if user_role == 'admin':
        lista_catequizandos_final = list(db.catequizandos.aggregate(pipeline_base))

    elif user_role == 'catequista':
        # 1. Encontrar los grupos que maneja este catequista
        grupos_del_catequista = list(db.grupos.find({'catequista_id': user_id}))
        if grupos_del_catequista:
            # 2. Obtener los IDs de esos grupos
            ids_de_mis_grupos = [g['_id'] for g in grupos_del_catequista]
            # 3. Construir el filtro para buscar catequizandos en esos grupos
            filtro_alumnos = {"$match": {"grupo_id": {"$in": ids_de_mis_grupos}}}
            pipeline_catequista = [filtro_alumnos] + pipeline_base
            lista_catequizandos_final = list(db.catequizandos.aggregate(pipeline_catequista))

    elif user_role == 'catequizando':
        usuario = db.usuarios.find_one({'_id': user_id})
        if usuario and 'catequizando_id' in usuario:
            filtro_propio = {"$match": {"_id": usuario['catequizando_id']}}
            pipeline_catequizando = [filtro_propio] + pipeline_base
            lista_catequizandos_final = list(db.catequizandos.aggregate(pipeline_catequizando))
            
    return render_template('index.html', catequizandos=lista_catequizandos_final)

@app.route('/agregar_catequizando', methods=['GET', 'POST'])
@login_required(roles_permitidos=['admin'])
def agregar_catequizando():
    db = get_db()
    if request.method == 'POST':
        # ... (código existente para verificar cédula) ...
        
        grupo_id_str = request.form.get('grupo_id')
        grupo_id = ObjectId(grupo_id_str) if grupo_id_str else None

        db.catequizandos.insert_one({
            # ... (código existente de datos_personales, estado, etc.) ...
            "datos_personales": { ... },
            "estado": "Activo",
            "fecha_ingreso": datetime.now(),
            ### CAMBIO: Guardar el ID del grupo
            "grupo_id": grupo_id,
            "familiares": [], "sacramentos": [], "evaluaciones": [], "asistencias": []
        })
        flash('Catequizando agregado con éxito.', 'success')
        return redirect(url_for('index'))
    
    # ### CAMBIO: Pasar la lista de grupos a la plantilla
    grupos = list(db.grupos.find({}))
    return render_template('agregar_catequizando.html', grupos=grupos)

@app.route('/editar_catequizando/<id>', methods=['GET', 'POST'])
@login_required(roles_permitidos=['admin'])
def editar_catequizando(id):
    db = get_db()
    # ... (código existente para el try-except del ObjectId) ...
    filtro = {'_id': ObjectId(id)}
    
    if request.method == 'POST':
        grupo_id_str = request.form.get('grupo_id')
        grupo_id = ObjectId(grupo_id_str) if grupo_id_str else None

        db.catequizandos.update_one(filtro, {"$set": {
            # ... (código existente para actualizar datos_personales y estado) ...
            "datos_personales.nombres": ...,
            ### CAMBIO: Actualizar el ID del grupo
            "grupo_id": grupo_id
        }})
        flash('Datos del catequizando actualizados con éxito.', 'success')
        return redirect(url_for('index'))
    
    catequizando = db.catequizandos.find_one(filtro)
    # ... (código existente para verificar si se encontró el catequizando) ...
    
    # ### CAMBIO: Pasar la lista de grupos a la plantilla
    grupos = list(db.grupos.find({}))
    return render_template('editar_catequizando.html', catequizando=catequizando, grupos=grupos)

@app.route('/eliminar_catequizando/<id>', methods=['POST'])
@login_required(roles_permitidos=['admin']) # Solo admins
def eliminar_catequizando(id):
    db = get_db()
    try:
        object_id = ObjectId(id)
    except:
        flash("ID de catequizando no válido.", "error")
        return redirect(url_for('index'))

    # También deberíamos eliminar el usuario asociado, si existe
    catequizando_a_eliminar = db.catequizandos.find_one({'_id': object_id})
    if catequizando_a_eliminar:
        db.usuarios.delete_many({'catequizando_id': object_id})

    resultado = db.catequizandos.delete_one({'_id': object_id})
    
    if resultado.deleted_count > 0:
        flash('Catequizando y su usuario asociado (si existía) han sido eliminados.', 'success')
    else:
        flash('No se encontró el catequizando para eliminar.', 'warning')
        
    return redirect(url_for('index'))

# --- 7. RUTAS DE GESTIÓN DE GRUPOS (NUEVO) ---

@app.route('/grupos')
@login_required(roles_permitidos=['admin'])
def lista_grupos():
    db = get_db()
    # Hacemos un "lookup" para traer el nombre del catequista en lugar de solo su ID
    pipeline = [
        {
            "$lookup": {
                "from": "usuarios",
                "localField": "catequista_id",
                "foreignField": "_id",
                "as": "catequista_info"
            }
        },
        {
            "$unwind": {
                "path": "$catequista_info",
                "preserveNullAndEmptyArrays": True # Para que no desaparezcan grupos sin catequista
            }
        }
    ]
    grupos = list(db.grupos.aggregate(pipeline))
    return render_template('lista_grupos.html', grupos=grupos)

@app.route('/agregar_grupo', methods=['GET', 'POST'])
@login_required(roles_permitidos=['admin'])
def agregar_grupo():
    db = get_db()
    if request.method == 'POST':
        catequista_id_str = request.form.get('catequista_id')
        catequista_id = ObjectId(catequista_id_str) if catequista_id_str else None

        db.grupos.insert_one({
            'nombre': request.form['nombre'],
            'descripcion': request.form.get('descripcion', ''),
            'catequista_id': catequista_id
        })
        flash('Grupo creado con éxito.', 'success')
        return redirect(url_for('lista_grupos'))

    # Buscamos todos los usuarios con rol 'catequista' para el dropdown
    catequistas = list(db.usuarios.find({'rol': 'catequista'}))
    return render_template('agregar_grupo.html', catequistas=catequistas)


# --- 6. INICIAR LA APLICACIÓN ---
if __name__ == '__main__':
    app.run(debug=True, port=5001) # Usar un puerto diferente a 5000 es una buena práctica a veces