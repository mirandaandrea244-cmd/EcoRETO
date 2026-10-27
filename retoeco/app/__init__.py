import os
import sqlite3
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, g

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "eco_reto.db")


def get_db():
    """Abre (una sola vez por petición) la conexión a la base de datos."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row  # permite usar fila["columna"]
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Crea las tablas si todavía no existen."""
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS acciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            fecha TEXT NOT NULL,
            cantidad REAL NOT NULL,
            unidad TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        );
    """)
    db.commit()
    db.close()


def create_app():
    # templates y static están junto a app/, por eso "../"
    app = Flask(__name__,
                template_folder="../templates",
                static_folder="../static",
                static_url_path="/static")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "clave-local-eco-reto")
    app.teardown_appcontext(close_db)
    init_db()

    from .routes import bp
    app.register_blueprint(bp)
    return app