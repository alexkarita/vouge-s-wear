import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # ── Configuration ─────────────────────────────────────────────────────────
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'vogues-wear-super-secret-key-alex-karita-2026-xk9!')

    # ── Database ──────────────────────────────────────────────────────────────
    # On Render: SQLite stored in /tmp so it persists during the session
    # For production use PostgreSQL by setting DATABASE_URL in environment variables
    database_url = os.getenv('DATABASE_URL', '')

    if database_url:
        # Fix for older Render PostgreSQL URLs that start with postgres://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Use SQLite — works on both local and Render free tier
        db_path = os.path.join(app.instance_path, 'vogueswear.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ── Session config ────────────────────────────────────────────────────────
    app.config['SESSION_COOKIE_SECURE']   = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

    # ── Upload folder ─────────────────────────────────────────────────────────
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ── Initialize extensions ─────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    # ── Register blueprints ───────────────────────────────────────────────────
    from app.routes import main
    from app.admin_routes import admin_bp

    app.register_blueprint(main)
    app.register_blueprint(admin_bp)

    # ── Create all database tables on startup ─────────────────────────────────
    # This runs every time the app starts — safe to run multiple times
    with app.app_context():
        db.create_all()
        print("✅ Database tables created/verified.")

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))