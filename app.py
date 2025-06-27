# archivo: app.py (VERSIÓN FINAL Y CORREGIDA)
# Propósito: El corazón de la aplicación web.

# --- 1. IMPORTACIONES ---
from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import get_db
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# --- 2. CONFIGURACIÓN DE LA APLICACIÓN ---
app = Flask(__name__)
app.secret_key = 'un-secreto-muy-bien-guardado-para-el-proyecto'

# --- 3. DECORADOR DE AUTENTICACIÓN (LÓGICA DE PERMISOS CORREGIDA) ---
def login_required(role="any"):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Debes iniciar sesión para acceder a esta página.", "warning")
                return redirect(url_for('login'))

            user_role = session.get('role')
            # ----- LÓGICA CORREGIDA -----
            # Si el rol del usuario no es 'admin' (que puede todo)
            # Y si se requiere un rol específico (no es 'any')
            # Y si el rol del usuario no es el requerido
            if user_role != 'admin' and role != "any" and user_role != role:
                flash("No tienes los permisos necesarios para realizar esta acción.", "error")
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- 4. RUTAS DE AUTENTICACIÓN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect(url_for('index'))
    if request.method == 'POST':
        db = get_db()
        if db is None:
            flash("Error crítico de conexión con la DB.", "error")
            return render_template('login.html')
        
        usuario_db = db.usuarios.find_one({'usuario': request.form['usuario']})
        if usuario_db and check_password_hash(usuario_db['contrasena'], request.form['contrasena']):
            session['user_id'] = str(usuario_db['_id'])
            session['usuario'] = usuario_db['usuario']
            session['rol'] = usuario_db['rol']
            flash(f"¡Bienvenido de vuelta, {session['usuario']}!", 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))

@app.route('/registrar_usuario', methods=['GET', 'POST'])
@login_required(role='admin') # Protegemos esta ruta, solo admins pueden registrar nuevos usuarios
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
        if request.form['rol'] == 'catequizando' and request.form.get('cedula_asociada'):
            catequizando = db.catequizandos.find_one({'datos_personales.cedula': request.form['cedula_asociada']})
            if catequizando:
                nuevo_usuario['catequizando_id'] = catequizando['_id']
            else:
                flash(f"Cédula {request.form['cedula_asociada']} no encontrada en catequizandos.", "warning")
        
        db.usuarios.insert_one(nuevo_usuario)
        flash(f"Usuario '{request.form['usuario']}' registrado con éxito.", "success")
        return redirect(url_for('login'))
    return render_template('registrar_usuario.html')

# --- 5. RUTAS PRINCIPALES Y CRUD ---
@app.route('/')
@login_required()
def index():
    db = get_db()
    lista_catequizandos = []
    
    if db is not None:
        if session['rol'] == 'catequizando':
            usuario = db.usuarios.find_one({'_id': ObjectId(session['user_id'])})
            if usuario and 'catequizando_id' in usuario:
                catequizando = db.catequizandos.find_one({'_id': usuario['catequizando_id']})
                if catequizando:
                    lista_catequizandos.append(catequizando)
        else: # admin y catequista ven todo
            lista_catequizandos = list(db.catequizandos.find({}))
    else:
        flash("Error de conexión con la DB.", "error")
        
    return render_template('index.html', catequizandos=lista_catequizandos)

@app.route('/agregar_catequizando', methods=['GET', 'POST'])
@login_required(role='admin')
def agregar_catequizando():
    if request.method == 'POST':
        db = get_db()
        db.catequizandos.insert_one({
            "datos_personales": { "nombres": request.form['nombres'], "apellidos": request.form['apellidos'], "cedula": request.form['cedula'], "fecha_nacimiento": datetime.strptime(request.form['fecha_nacimiento'], '%Y-%m-%d'), "genero": request.form.get('genero')},
            "estado": "Activo", "fecha_ingreso": datetime.now(), "familiares": [], "sacramentos": [], "evaluaciones": [], "asistencias": [], "certificados": []
        })
        flash('Catequizando agregado con éxito.', 'success')
        return redirect(url_for('index'))
    return render_template('agregar_catequizando.html')

@app.route('/editar_catequizando/<id>', methods=['GET', 'POST'])
@login_required(role='admin')
def editar_catequizando(id):
    db = get_db()
    filtro = {'_id': ObjectId(id)}
    if request.method == 'POST':
        db.catequizandos.update_one(filtro, {"$set": {
            "datos_personales.nombres": request.form['nombres'], "datos_personales.apellidos": request.form['apellidos'], "datos_personales.cedula": request.form['cedula'], "datos_personales.fecha_nacimiento": datetime.strptime(request.form['fecha_nacimiento'], '%Y-%m-%d'), "datos_personales.genero": request.form.get('genero'), "estado": request.form.get('estado')
        }})
        flash('Catequizando actualizado.', 'success')
        return redirect(url_for('index'))
    catequizando = db.catequizandos.find_one(filtro)
    return render_template('editar_catequizando.html', catequizando=catequizando)

@app.route('/eliminar_catequizando/<id>', methods=['POST'])
@login_required(role='admin')
def eliminar_catequizando(id):
    db = get_db()
    db.catequizandos.delete_one({'_id': ObjectId(id)})
    flash('Catequizando eliminado.', 'success')
    return redirect(url_for('index'))

# --- 6. INICIAR LA APLICACIÓN ---
if __name__ == '__main__':
    app.run(debug=True)