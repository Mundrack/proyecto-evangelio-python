# archivo: app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from database import get_db
from bson.objectid import ObjectId
from datetime import datetime

# Inicialización de la aplicación Flask
app = Flask(__name__)
# Necesitamos una clave secreta para usar 'flash messages'
app.secret_key = 'mi_clave_secreta_super_segura' 

# Ruta principal: Muestra el formulario para agregar catequizandos
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 1. Recibir datos del formulario
        nombres = request.form['nombres']
        apellidos = request.form['apellidos']
        cedula = request.form['cedula']
        fecha_nac_str = request.form['fecha_nacimiento']

        # Validar que los campos no estén vacíos
        if not all([nombres, apellidos, cedula, fecha_nac_str]):
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('index'))

        # 2. Conectar a la DB y preparar el documento
        db = get_db()
        if db is not None:
            catequizandos_collection = db.catequizandos
            
            # Convertir la fecha de string a objeto datetime
            fecha_nacimiento = datetime.strptime(fecha_nac_str, '%Y-%m-%d')
            
            nuevo_catequizando = {
                "datos_personales": {
                    "nombres": nombres,
                    "apellidos": apellidos,
                    "cedula": cedula,
                    "fecha_nacimiento": fecha_nacimiento,
                    "genero": request.form.get('genero', 'O'), # Usar .get para campos opcionales
                    "fecha_registro": datetime.now()
                },
                "estado": "Activo",
                "fecha_ingreso": datetime.now(),
                "familiares": [],
                "sacramentos": [],
                "evaluaciones": [],
                "certificados": []
            }
            
            # 3. Insertar en la base de datos
            catequizandos_collection.insert_one(nuevo_catequizando)
            flash('¡Catequizando agregado con éxito!', 'success')
        else:
            flash('Error de conexión con la base de datos.', 'error')

        # Redirigir a la misma página para limpiar el formulario
        return redirect(url_for('index'))

    # Si el método es GET, simplemente muestra la página
    return render_template('index.html')

# Ruta para la página de consulta
@app.route('/consultar', methods=['GET', 'POST'])
def consultar():
    resultado = None
    if request.method == 'POST':
        cedula_a_buscar = request.form['cedula_busqueda']
        db = get_db()
        if db is not None:
            # Buscar un solo documento que coincida con la cédula
            resultado = db.catequizandos.find_one({"datos_personales.cedula": cedula_a_buscar})
            if not resultado:
                flash(f'No se encontró ningún catequizando con la cédula {cedula_a_buscar}.', 'warning')
        else:
            flash('Error de conexión con la base de datos.', 'error')
    
    # Renderizar la plantilla, pasándole el resultado (que puede ser None o el documento encontrado)
    return render_template('consulta.html', resultado=resultado)

# Esto permite ejecutar la aplicación directamente con 'python app.py'
if __name__ == '__main__':
    app.run(debug=True)