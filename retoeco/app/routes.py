import os
import sqlite3
from flask import current_app
from datetime import date
from functools import wraps

from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, abort)
from werkzeug.security import generate_password_hash, check_password_hash

from . import get_db

bp = Blueprint("main", __name__)

# Tipos de acción: icono, color, unidad sugerida y mensaje de impacto
TIPOS = {
    "Reciclaje": {"unidad": "kg", "icono": "♻️", "clase": "verde",
                  "mensaje": "Al reciclar reduces la basura y le das una segunda vida a los materiales."},
    "Ahorro de agua": {"unidad": "litros", "icono": "💧", "clase": "azul",
                       "mensaje": "Con esta acción ayudas a conservar el agua, un recurso vital para todas las formas de vida."},
    "Transporte": {"unidad": "kg CO₂", "icono": "🚲", "clase": "amarillo",
                   "mensaje": "Moverte sin contaminar reduce las emisiones y mejora el aire que respiramos."},
    "Energía": {"unidad": "kWh", "icono": "💡", "clase": "morado",
                "mensaje": "Ahorrar energía disminuye la contaminación y cuida los recursos del planeta."},
    "Plantación": {"unidad": "kg CO₂", "icono": "🌳", "clase": "verde",
                   "mensaje": "Las plantas limpian el aire, dan sombra y son hogar de muchos animales."},
}
UNIDADES = ["kg", "litros", "kg CO₂", "kWh"]


@bp.app_context_processor
def datos_globales():
    """Hace que TIPOS y UNIDADES estén disponibles en todos los HTML."""
    return {"TIPOS": TIPOS, "UNIDADES": UNIDADES}


@bp.app_template_filter("num")
def num(valor):
    """5.0 -> '5'   |   2.50 -> '2.5'"""
    return f"{valor:,.2f}".rstrip("0").rstrip(".")


def login_requerido(vista):
    """Si no hay sesión iniciada, manda al login."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("main.login"))
        return vista(*args, **kwargs)
    return envoltura


def obtener_accion(id):
    """Busca una acción SOLO si pertenece al usuario que inició sesión."""
    accion = get_db().execute(
        "SELECT * FROM acciones WHERE id = ? AND usuario_id = ?",
        (id, session["usuario_id"])).fetchone()
    if accion is None:
        abort(404)
    return accion


def validar(form):
    """Valida el formulario en el servidor (por si falla el JavaScript)."""
    errores = []
    tipo = form.get("tipo", "")
    descripcion = form.get("descripcion", "").strip()
    fecha = form.get("fecha", "")
    unidad = form.get("unidad", "")
    cantidad = None

    if tipo not in TIPOS:
        errores.append("Elige un tipo de acción válido.")
    if len(descripcion) < 5:
        errores.append("La descripción necesita al menos 5 caracteres.")
    if not fecha:
        errores.append("Elige una fecha.")
    if unidad not in UNIDADES:
        errores.append("Elige una unidad válida.")
    try:
        cantidad = float(form.get("cantidad", ""))
        if cantidad <= 0:
            errores.append("El impacto debe ser mayor que 0.")
    except ValueError:
        errores.append("El impacto debe ser un número.")

    return errores, (tipo, descripcion, fecha, cantidad, unidad)


# ---------- Acceso ----------
@bp.route("/")
def raiz():
    return redirect(url_for("main.inicio" if "usuario_id" in session else "main.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")
        fila = get_db().execute(
            "SELECT * FROM usuarios WHERE usuario = ?", (usuario,)).fetchone()
        if fila and check_password_hash(fila["password"], password):
            session.clear()
            session["usuario_id"] = fila["id"]
            session["usuario"] = fila["usuario"]
            return redirect(url_for("main.inicio"))
        flash("Usuario o contraseña incorrectos.", "fallo")
    return render_template("login.html", modo="login")


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")
        if len(usuario) < 3 or len(password) < 4:
            flash("El usuario necesita 3 letras o más y la contraseña 4 o más.", "fallo")
        else:
            try:
                db = get_db()
                db.execute("INSERT INTO usuarios (usuario, password) VALUES (?, ?)",
                           (usuario, generate_password_hash(password)))
                db.commit()
                flash("¡Cuenta creada! Ya puedes iniciar sesión 🌱", "ok")
                return redirect(url_for("main.login"))
            except sqlite3.IntegrityError:
                flash("Ese usuario ya existe, prueba con otro.", "fallo")
    return render_template("login.html", modo="registro")


@bp.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada. ¡Hasta pronto! 👋", "ok")
    return redirect(url_for("main.login"))


# ---------- CRUD de acciones ----------
@bp.route("/inicio")
@login_requerido
def inicio():
    uid = session["usuario_id"]
    db = get_db()
    acciones = db.execute(
        "SELECT * FROM acciones WHERE usuario_id = ? ORDER BY fecha DESC, id DESC",
        (uid,)).fetchall()

    def suma(unidad):
        fila = db.execute(
            "SELECT COALESCE(SUM(cantidad), 0) AS total FROM acciones "
            "WHERE usuario_id = ? AND unidad = ?", (uid, unidad)).fetchone()
        return fila["total"]

    stats = {"total": len(acciones), "litros": suma("litros"),
             "kg": suma("kg"), "co2": suma("kg CO₂")}
    return render_template("index.html", acciones=acciones, stats=stats)


@bp.route("/acciones/nueva", methods=["GET", "POST"])
@login_requerido
def nueva():
    if request.method == "POST":
        errores, datos = validar(request.form)
        if errores:
            for e in errores:
                flash(e, "fallo")
            return render_template("formulario.html", modo="nueva", accion=request.form)
        db = get_db()
        db.execute(
            "INSERT INTO acciones (usuario_id, tipo, descripcion, fecha, cantidad, unidad) "
            "VALUES (?, ?, ?, ?, ?, ?)", (session["usuario_id"],) + datos)
        db.commit()
        flash("¡Acción guardada! Gracias por cuidar el planeta 🌍", "ok")
        return redirect(url_for("main.inicio"))
    return render_template("formulario.html", modo="nueva",
                           accion={"fecha": date.today().isoformat()})


@bp.route("/acciones/<int:id>")
@login_requerido
def detalle(id):
    return render_template("detalle.html", accion=obtener_accion(id))


@bp.route("/acciones/<int:id>/editar", methods=["GET", "POST"])
@login_requerido
def editar(id):
    accion = obtener_accion(id)
    if request.method == "POST":
        errores, datos = validar(request.form)
        if errores:
            for e in errores:
                flash(e, "fallo")
            return render_template("formulario.html", modo="editar", accion=request.form)
        db = get_db()
        db.execute(
            "UPDATE acciones SET tipo = ?, descripcion = ?, fecha = ?, cantidad = ?, unidad = ? "
            "WHERE id = ? AND usuario_id = ?", datos + (id, session["usuario_id"]))
        db.commit()
        flash("Acción actualizada ✅", "ok")
        return redirect(url_for("main.detalle", id=id))
    return render_template("formulario.html", modo="editar", accion=dict(accion))


@bp.route("/acciones/<int:id>/eliminar", methods=["POST"])
@login_requerido
def eliminar(id):
    obtener_accion(id)  # confirma que existe y es tuya
    db = get_db()
    db.execute("DELETE FROM acciones WHERE id = ? AND usuario_id = ?",
               (id, session["usuario_id"]))
    db.commit()
    flash("Acción eliminada 🗑️", "ok")
    return redirect(url_for("main.inicio"))

# ---------- Foto de perfil ----------
EXTENSIONES = {"png", "jpg", "jpeg", "gif", "webp"}


def carpeta_fotos():
    ruta = os.path.abspath(os.path.join(current_app.root_path, "..", "static", "uploads"))
    os.makedirs(ruta, exist_ok=True)
    return ruta


def buscar_foto(uid):
    """Busca la foto del usuario (se guarda como user1.jpg, user2.png, etc.)."""
    for archivo in os.listdir(carpeta_fotos()):
        if archivo.startswith(f"user{uid}."):
            return archivo
    return None


@bp.app_context_processor
def foto_global():
    """Deja disponible 'foto_perfil' en todos los HTML."""
    uid = session.get("usuario_id")
    return {"foto_perfil": buscar_foto(uid) if uid else None}


@bp.route("/foto", methods=["POST"])
@login_requerido
def subir_foto():
    archivo = request.files.get("foto")
    if archivo and archivo.filename:
        extension = archivo.filename.rsplit(".", 1)[-1].lower()
        archivo.seek(0, os.SEEK_END)
        peso = archivo.tell()
        archivo.seek(0)
        if extension not in EXTENSIONES:
            flash("Solo se permiten imágenes PNG, JPG, GIF o WEBP.", "fallo")
        elif peso > 2 * 1024 * 1024:
            flash("La foto pesa más de 2 MB, prueba con una más pequeña.", "fallo")
        else:
            uid = session["usuario_id"]
            vieja = buscar_foto(uid)
            if vieja:
                os.remove(os.path.join(carpeta_fotos(), vieja))
            archivo.save(os.path.join(carpeta_fotos(), f"user{uid}.{extension}"))
            flash("¡Foto de perfil actualizada! 📸", "ok")
    return redirect(request.referrer or url_for("main.inicio"))