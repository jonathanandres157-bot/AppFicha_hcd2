from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import sys

# Permite importar el módulo fhir desde la subcarpeta
sys.path.insert(0, os.path.dirname(__file__))
from fhir.fhir_service import (
    crear_paciente_completo, listar_pacientes, obtener_ficha_completa,
    obtener_resumen_paciente,
    eliminar_paciente as fhir_eliminar,
    resetear_paciente as fhir_resetear,
    modificar_ficha_completa, obtener_ficha_para_edicion,
    iniciar_atencion as fhir_iniciar_atencion,
    obtener_encuentro_activo as fhir_encuentro_activo,
    obtener_recursos_atencion,
    obtener_obs_phantom as fhir_obs_phantom,
    construir_recurso_atencion,
    registrar_recurso_atencion_fhir,
    finalizar_atencion as fhir_finalizar_atencion,
    obtener_detalle_atencion as fhir_detalle_atencion,
    listar_atenciones_paciente,
)

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY', 'clave-de-respaldo-solo-local')
# ------------------------------------------------------------
# Usuarios de prueba 
# Roles: 'profesor' o 'estudiante'
# ------------------------------------------------------------

USUARIOS = {
    'AdminProfesor': {'password': '1234', 'rol': 'profesor',   'nombre': 'Admin'},
    'alumno01':   {'password': '1234', 'rol': 'estudiante', 'nombre': 'Alumno'},
}

# ──────────────────────────────────────────────────────────────
# RUTAS
# ──────────────────────────────────────────────────────────────
 
 #pantalla de inicio de sesión
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'usuario' in session:
        return redirect(url_for('pacientes'))
 
    if request.method == 'POST':
        usuario  = request.form.get('usuario', '').strip()
        password = request.form.get('password', '').strip()
 
        if usuario in USUARIOS and USUARIOS[usuario]['password'] == password:
            session['usuario'] = usuario
            session['rol']     = USUARIOS[usuario]['rol']
            session['nombre']  = USUARIOS[usuario]['nombre']
            return redirect(url_for('pacientes'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')
 
    return render_template('login.html')
 
 #pantalla de pacientes precargados/lista de pacientes
@app.route('/pacientes')
def pacientes():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    pacientes_lista = listar_pacientes()

    return render_template(
        'pacientes.html',
        pacientes=pacientes_lista,
        rol=session.get('rol'),
        nombre=session.get('nombre'),
    )
 
 #para crear un paciente
@app.route('/pacientes/crear', methods=['GET', 'POST'])
def crear_paciente():
    if 'usuario' not in session:
        return redirect(url_for('login'))
 
    if request.method == 'POST':
        print("[APP] Recibiendo formulario de creación de paciente...")
 
        # Llamar al servicio FHIR
        patient_id, nombre_completo = crear_paciente_completo(request.form)
 
        if patient_id:
            flash(f'Paciente "{nombre_completo}" creado exitosamente.', 'success')
            return redirect(url_for('pacientes'))
        else:
            flash('Error al crear el paciente en el servidor FHIR. Intenta nuevamente.', 'error')
 
    return render_template(
        'crear_paciente.html',
        rol=session.get('rol'),
        nombre=session.get('nombre'),
    )
 
 #para ver ficha del paciente
@app.route('/pacientes/<patient_id>')
def ficha_paciente(patient_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    ficha = obtener_ficha_completa(patient_id)
    if not ficha:
        flash('No se pudo obtener la ficha del paciente.', 'error')
        return redirect(url_for('pacientes'))

    # Usar el ID de sesión para no depender del índice de búsqueda
    enc_id_sesion = session.get(f'enc_{patient_id}')
    encuentro_activo = fhir_encuentro_activo(patient_id, enc_id_sesion)

    return render_template('ficha_paciente.html',
                           ficha=ficha,
                           rol=session.get('rol'),
                           nombre=session.get('nombre'),
                           encuentro_activo=encuentro_activo)


@app.route('/pacientes/<patient_id>/actualizar', methods=['GET', 'POST'])
def actualizar_ficha(patient_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    if session.get('rol') == 'estudiante':
        enc_id_sesion = session.get(f'enc_{patient_id}')
        enc = fhir_encuentro_activo(patient_id, enc_id_sesion)
        if enc:
            return redirect(url_for('atencion_route', patient_id=patient_id))
        flash('Debes iniciar una atención para registrar datos clínicos.', 'info')
        return redirect(url_for('ficha_paciente', patient_id=patient_id))
    return redirect(url_for('modificar_ficha', patient_id=patient_id))

#pantalla para modificar datos del paciente (solo profesor)
@app.route('/pacientes/<patient_id>/modificar', methods=['GET', 'POST'])
def modificar_ficha(patient_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    if session.get('rol') != 'profesor':
        flash('No tienes permisos para modificar fichas.', 'error')
        return redirect(url_for('pacientes'))
    if request.method == 'POST':
        modificar_ficha_completa(patient_id, request.form)
        flash('Ficha modificada correctamente.', 'success')
        return redirect(url_for('ficha_paciente', patient_id=patient_id))
    ficha = obtener_ficha_para_edicion(patient_id)
    if not ficha:
        flash('No se encontró el paciente.', 'error')
        return redirect(url_for('pacientes'))
    return render_template('modificar_ficha.html', ficha=ficha,
                           rol=session.get('rol'), nombre=session.get('nombre'))


# Para elimianr paciente
@app.route('/pacientes/<patient_id>/eliminar', methods=['POST'])
def eliminar_paciente(patient_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    if session.get('rol') != 'profesor':
        flash('No tienes permisos para eliminar pacientes.', 'error')
        return redirect(url_for('pacientes'))
    fhir_eliminar(patient_id)
    flash('Paciente eliminado correctamente.', 'success')
    return redirect(url_for('pacientes'))


@app.route('/pacientes/<patient_id>/resetear', methods=['POST'])
def resetear_paciente_route(patient_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    if session.get('rol') != 'profesor':
        flash('No tienes permisos para resetear pacientes.', 'error')
        return redirect(url_for('pacientes'))
    fhir_resetear(patient_id)
    flash('Paciente reseteado. Datos clínicos eliminados, datos personales conservados.', 'success')
    return redirect(url_for('ficha_paciente', patient_id=patient_id))


@app.route('/logout')
def logout():
    """Cierre de sesión."""
    session.clear()
    return redirect(url_for('login'))
 
 
# ────────agregardo para encounter──────────
@app.route('/pacientes/<patient_id>/iniciar-atencion', methods=['POST'])
def iniciar_atencion_route(patient_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    if session.get('rol') != 'estudiante':
        flash('Solo estudiantes pueden iniciar atenciones.', 'error')
        return redirect(url_for('ficha_paciente', patient_id=patient_id))

    # Primero verifica si ya existe uno activo
    enc_activo = fhir_encuentro_activo(patient_id)
    if enc_activo:
        # Guarda en sesión por si acaso no estaba
        session[f'enc_{patient_id}'] = enc_activo['encounter_id']
        return redirect(url_for('atencion_route', patient_id=patient_id))

    pac  = obtener_resumen_paciente(patient_id) or {}
    rut  = pac.get('rut', '')
    encounter_id, inicio = fhir_iniciar_atencion(patient_id, rut, session.get('usuario', ''))
    if not encounter_id:
        flash('Error al crear la atención en el servidor FHIR.', 'error')
        return redirect(url_for('ficha_paciente', patient_id=patient_id))

    # Guardar en sesión para el GET directo inmediato 
    session[f'enc_{patient_id}'] = encounter_id

    return redirect(url_for('atencion_route', patient_id=patient_id))


@app.route('/pacientes/<patient_id>/atencion')
def atencion_route(patient_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    if session.get('rol') != 'estudiante':
        flash('Solo estudiantes acceden a la pantalla de atención.', 'error')
        return redirect(url_for('ficha_paciente', patient_id=patient_id))

    # Usa el ID guardado en sesión para GET directo 
    enc_id_sesion = session.get(f'enc_{patient_id}')
    encuentro = fhir_encuentro_activo(patient_id, enc_id_sesion)
    if not encuentro:
        session.pop(f'enc_{patient_id}', None)
        flash('No hay atención activa para este paciente.', 'error')
        return redirect(url_for('ficha_paciente', patient_id=patient_id))

    pac = obtener_resumen_paciente(patient_id) or {}
    encuentro['nombre_paciente'] = f"{pac.get('nombre','')} {pac.get('apellido','')}".strip()

    recursos = obtener_recursos_atencion(
        patient_id, encuentro['encounter_id'], encuentro['inicio']
    )
    return render_template('atencion.html',
                           encuentro=encuentro, recursos=recursos,
                           rol=session.get('rol'), nombre=session.get('nombre'))


@app.route('/pacientes/<patient_id>/atencion/obs-phantom')
def obs_phantom_route(patient_id):
    if 'usuario' not in session: return {'error': 'No autenticado'}, 401

    # Usar el ID de sesión igual que en atencion_route
    enc_id_sesion = session.get(f'enc_{patient_id}')
    encuentro = fhir_encuentro_activo(patient_id, enc_id_sesion)
    if not encuentro: return {'error': 'Sin atención activa'}, 400

    obs_dashboard, obs_ids = fhir_obs_phantom(patient_id, encuentro.get('inicio'))
    return {'obs_dashboard': obs_dashboard, 'total': len(obs_ids)}


@app.route('/pacientes/<patient_id>/atencion/agregar', methods=['POST'])
def agregar_recurso_route(patient_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    encounter_id = request.form.get('encounter_id', '').strip()
    if not encounter_id:
        if es_ajax: return {'success': False, 'message': 'Sin ID de encuentro.'}, 400
        flash('Sin atención activa.', 'error')
        return redirect(url_for('ficha_paciente', patient_id=patient_id))

    tipo = request.form.get('tipo')
    fhir_resource, display = construir_recurso_atencion(
        patient_id, encounter_id, tipo, request.form)

    if not fhir_resource:
        if es_ajax: return {'success': False, 'message': 'Verifica los campos requeridos.'}, 400
        flash('No se pudo registrar.', 'error')
        return redirect(url_for('atencion_route', patient_id=patient_id))

    resp = registrar_recurso_atencion_fhir(tipo, fhir_resource)
    if resp:
        if es_ajax: return {'success': True, 'tipo': tipo, 'display': display}
        flash('Registrado.', 'success')
    else:
        if es_ajax: return {'success': False, 'message': 'Error al guardar en el servidor FHIR.'}, 500
        flash('No se pudo registrar en el servidor.', 'error')

    return redirect(url_for('atencion_route', patient_id=patient_id))

@app.route('/pacientes/<patient_id>/finalizar-atencion', methods=['POST'])
def finalizar_atencion_route(patient_id):
    if 'usuario' not in session: return redirect(url_for('login'))

    encounter_id = request.form.get('encounter_id', '').strip()
    if not encounter_id:
        flash('Sin atención activa para finalizar.', 'error')
        return redirect(url_for('ficha_paciente', patient_id=patient_id))

    fhir_finalizar_atencion(
        patient_id,
        encounter_id,
        request.form.get('nota_adicional', ''),
        session.get('usuario', ''),
    )

    # Limpiar la clave de sesión del encuentro
    session.pop(f'enc_{patient_id}', None)

    flash('Atención finalizada. Todos los recursos han sido subidos al servidor.', 'success')
    return redirect(url_for('ficha_paciente', patient_id=patient_id))


@app.route('/pacientes/<patient_id>/historial')
def historial_route(patient_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    atenciones = listar_atenciones_paciente(patient_id)
    pac        = obtener_resumen_paciente(patient_id) or {}
    nombre_pac = f"{pac.get('nombre','')} {pac.get('apellido','')}".strip() or patient_id
    return render_template('historial_atenciones.html',
                           atenciones=atenciones, patient_id=patient_id,
                           nombre_paciente=nombre_pac,
                           rol=session.get('rol'), nombre=session.get('nombre'))


@app.route('/pacientes/<patient_id>/historial/<bundle_id>')
def detalle_atencion_route(patient_id, bundle_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    detalle = fhir_detalle_atencion(bundle_id=bundle_id)
    if not detalle:
        flash('No se pudo recuperar el detalle.', 'error')
        return redirect(url_for('historial_route', patient_id=patient_id))
    pac        = obtener_resumen_paciente(patient_id) or {}
    nombre_pac = f"{pac.get('nombre','')} {pac.get('apellido','')}".strip() or patient_id
    return render_template('detalle_atencion.html',
                           detalle=detalle, patient_id=patient_id,
                           nombre_paciente=nombre_pac,
                           rol=session.get('rol'), nombre=session.get('nombre'))

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
