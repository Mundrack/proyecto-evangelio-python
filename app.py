# --- 1. IMPORTACIONES ---
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
from functools import wraps

# Importamos nuestra función para obtener la base de datos
from database import get_db

# --- 2. CONFIGURACIÓN INICIAL DE LA APLICACIÓN ---
app = Flask(__name__)

# La 'SECRET_KEY' es fundamental para gestionar las sesiones de usuario (cookies seguras).
# La cargamos desde el archivo .env para mantenerla segura.
app.secret_key = os.getenv('SECRET_KEY', 'una-clave-por-defecto-si-no-hay-env')

# --- 3. DECORADOR DE PERMISOS (CONTROL DE ACCESO) ---
def login_required(roles_permitidos=None):
    """
    Decorador personalizado para proteger rutas.
    Verifica si un usuario ha iniciado sesión y si su rol le permite acceder a la ruta.
    
    Args:
        roles_permitidos (list, optional): Una lista de strings con los roles que pueden
                                            acceder. Si es None, solo se requiere estar logueado.
    """
    if roles_permitidos is None:
        roles_permitidos = []

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Verificar si hay un usuario en la sesión.
            if 'user_id' not in session:
                flash("Debes iniciar sesión para acceder a esta página.", "warning")
                return redirect(url_for('login'))

            user_role = session.get('rol')

            # 2. El rol 'admin' tiene acceso universal.
            if user_role == 'admin':
                return f(*args, **kwargs)

            # 3. Si la ruta no exige roles específicos, cualquier usuario logueado puede pasar.
            if not roles_permitidos:
                return f(*args, **kwargs)

            # 4. Verificar si el rol del usuario está en la lista de roles permitidos.
            if user_role in roles_permitidos:
                return f(*args, **kwargs)
            
            # 5. Si no cumple ninguna condición, se le niega el acceso.
            flash("No tienes los permisos necesarios para realizar esta acción.", "error")
            return redirect(url_for('index'))
        return decorated_function
    return decorator

# --- 4. RUTAS DE AUTENTICACIÓN (LOGIN, LOGOUT, REGISTRO) ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si el usuario ya está logueado, lo redirigimos al inicio.
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        db = get_db()
        # Buscamos al usuario por su nombre de usuario en la colección 'usuarios'.
        usuario_db = db.usuarios.find_one({'usuario': request.form['usuario']})
        
        # Verificamos si el usuario existe y si la contraseña es correcta.
        if usuario_db and check_password_hash(usuario_db.get('contrasena', ''), request.form['contrasena']):
            # Guardamos los datos del usuario en la sesión.
            session['user_id'] = str(usuario_db['_id'])
            session['usuario'] = usuario_db['usuario']
            session['rol'] = usuario_db['rol']
            session['nombre_completo'] = usuario_db.get('nombre_completo', usuario_db['usuario'])
            
            flash(f"¡Bienvenido de vuelta, {session['nombre_completo']}!", 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear() # Limpia todos los datos de la sesión.
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('login'))

@app.route('/registrar_usuario', methods=['GET', 'POST'])
@login_required(roles_permitidos=['admin']) # SOLO los administradores pueden registrar usuarios.
def registrar_usuario():
    if request.method == 'POST':
        db = get_db()
        # Evitar nombres de usuario duplicados.
        if db.usuarios.find_one({'usuario': request.form['usuario']}):
            flash(f"El nombre de usuario '{request.form['usuario']}' ya existe.", "error")
            return redirect(url_for('registrar_usuario'))
        
        nuevo_usuario = {
            'usuario': request.form['usuario'],
            'contrasena': generate_password_hash(request.form['contrasena']),
            'rol': request.form['rol'],
            'nombre_completo': request.form['nombre_completo']
        }
        
        # Si se está registrando un 'catequizando', intentamos vincularlo por su cédula.
        cedula_asociada = request.form.get('cedula_asociada')
        if request.form['rol'] == 'catequizando' and cedula_asociada:
            catequizando = db.catequizandos.find_one({'datos_personales.cedula': cedula_asociada})
            if catequizando:
                nuevo_usuario['catequizando_id'] = catequizando['_id']
            else:
                flash(f"Cédula '{cedula_asociada}' no encontrada. El usuario se creó sin vincular.", "warning")
        
        db.usuarios.insert_one(nuevo_usuario)
        flash(f"Usuario '{request.form['usuario']}' registrado con éxito.", "success")
        return redirect(url_for('index'))

    return render_template('registrar_usuario.html')

# --- 5. RUTA PRINCIPAL (VISTA DE INICIO) ---

@app.route('/')
@login_required() # Cualquier usuario logueado puede ver la página de inicio.
def index():
    db = get_db()
    lista_catequizandos_final = []
    
    user_role = session.get('rol')
    user_id = ObjectId(session.get('user_id'))
    
    # El 'pipeline' de agregación nos permite hacer consultas complejas, como unir colecciones.
    # Aquí lo usamos para traer el nombre del grupo junto con los datos del catequizando.
    pipeline_base = [
        {"$lookup": {"from": "grupos", "localField": "grupo_id", "foreignField": "_id", "as": "grupo_info"}},
        {"$unwind": {"path": "$grupo_info", "preserveNullAndEmptyArrays": True}}
    ]

    if user_role == 'admin':
        # El admin ve a todos los catequizandos.
        lista_catequizandos_final = list(db.catequizandos.aggregate(pipeline_base))

    elif user_role == 'catequista':
        # Un catequista solo ve a los alumnos de sus grupos.
        grupos_del_catequista = list(db.grupos.find({'catequista_id': user_id}))
        if grupos_del_catequista:
            ids_de_mis_grupos = [g['_id'] for g in grupos_del_catequista]
            filtro_alumnos = {"$match": {"grupo_id": {"$in": ids_de_mis_grupos}}}
            pipeline_catequista = [filtro_alumnos] + pipeline_base
            lista_catequizandos_final = list(db.catequizandos.aggregate(pipeline_catequista))

    elif user_role == 'catequizando':
        # Un catequizando solo se ve a sí mismo.
        usuario = db.usuarios.find_one({'_id': user_id})
        if usuario and 'catequizando_id' in usuario:
            filtro_propio = {"$match": {"_id": usuario['catequizando_id']}}
            pipeline_catequizando = [filtro_propio] + pipeline_base
            lista_catequizandos_final = list(db.catequizandos.aggregate(pipeline_catequizando))
            
    return render_template('index.html', catequizandos=lista_catequizandos_final)

# --- 6. RUTAS CRUD PARA CATEQUIZANDOS ---

@app.route('/agregar_catequizando', methods=['GET', 'POST'])
@login_required(roles_permitidos=['admin'])
def agregar_catequizando():
    db = get_db()
    if request.method == 'POST':
        if db.catequizandos.find_one({"datos_personales.cedula": request.form['cedula']}):
            flash(f"La cédula '{request.form['cedula']}' ya está registrada.", "error")
            return redirect(url_for('agregar_catequizando'))

        grupo_id_str = request.form.get('grupo_id')
        db.catequizandos.insert_one({
            "datos_personales": {
                "nombres": request.form['nombres'], "apellidos": request.form['apellidos'],
                "cedula": request.form['cedula'],
                "fecha_nacimiento": datetime.strptime(request.form['fecha_nacimiento'], '%Y-%m-%d'),
                "genero": request.form.get('genero')
            },
            "estado": "Activo", "fecha_ingreso": datetime.now(),
            "grupo_id": ObjectId(grupo_id_str) if grupo_id_str else None
        })
        flash('Catequizando agregado con éxito.', 'success')
        return redirect(url_for('index'))
    
    grupos = list(db.grupos.find({}))
    return render_template('agregar_catequizando.html', grupos=grupos)

@app.route('/editar_catequizando/<id>', methods=['GET', 'POST'])
@login_required(roles_permitidos=['admin'])
def editar_catequizando(id):
    db = get_db()
    filtro = {'_id': ObjectId(id)}
    
    if request.method == 'POST':
        grupo_id_str = request.form.get('grupo_id')
        db.catequizandos.update_one(filtro, {"$set": {
            "datos_personales.nombres": request.form['nombres'],
            "datos_personales.apellidos": request.form['apellidos'],
            "datos_personales.cedula": request.form['cedula'],
            "datos_personales.fecha_nacimiento": datetime.strptime(request.form['fecha_nacimiento'], '%Y-%m-%d'),
            "datos_personales.genero": request.form.get('genero'),
            "estado": request.form.get('estado'),
            "grupo_id": ObjectId(grupo_id_str) if grupo_id_str else None
        }})
        flash('Datos del catequizando actualizados.', 'success')
        return redirect(url_for('index'))
    
    catequizando = db.catequizandos.find_one(filtro)
    grupos = list(db.grupos.find({}))
    return render_template('editar_catequizando.html', catequizando=catequizando, grupos=grupos)

@app.route('/eliminar_catequizando/<id>', methods=['POST'])
@login_required(roles_permitidos=['admin'])
def eliminar_catequizando(id):
    db = get_db()
    obj_id = ObjectId(id)
    # También eliminamos las cuentas de usuario vinculadas a este catequizando.
    db.usuarios.delete_many({'catequizando_id': obj_id})
    db.catequizandos.delete_one({'_id': obj_id})
    flash('Catequizando y usuarios asociados eliminados.', 'success')
    return redirect(url_for('index'))

# --- 7. RUTAS CRUD PARA GRUPOS ---

@app.route('/grupos')
@login_required(roles_permitidos=['admin'])
def lista_grupos():
    db = get_db()
    pipeline = [
        {"$lookup": {"from": "usuarios", "localField": "catequista_id", "foreignField": "_id", "as": "catequista_info"}},
        {"$unwind": {"path": "$catequista_info", "preserveNullAndEmptyArrays": True}}
    ]
    grupos = list(db.grupos.aggregate(pipeline))
    return render_template('lista_grupos.html', grupos=grupos)

@app.route('/agregar_grupo', methods=['GET', 'POST'])
@login_required(roles_permitidos=['admin'])
def agregar_grupo():
    db = get_db()
    if request.method == 'POST':
        catequista_id_str = request.form.get('catequista_id')
        db.grupos.insert_one({
            'nombre': request.form['nombre'],
            'descripcion': request.form.get('descripcion', ''),
            'catequista_id': ObjectId(catequista_id_str) if catequista_id_str else None
        })
        flash('Grupo creado con éxito.', 'success')
        return redirect(url_for('lista_grupos'))

    catequistas = list(db.usuarios.find({'rol': 'catequista'}))
    return render_template('agregar_grupo.html', catequistas=catequistas)

# --- 8. INICIO DE LA APLICACIÓN ---
if __name__ == '__main__':
    # debug=True es útil para desarrollo, ya que recarga el servidor automáticamente con cada cambio.
    # Para producción, se debe cambiar a debug=False.
    app.run(debug=True, port=5001)