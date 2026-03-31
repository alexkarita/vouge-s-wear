import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# 1. Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # 2. Configuration
    # SECRET_KEY must be long and random — this fixes the cart session dropping
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'vogues-wear-super-secret-key-alex-karita-2026-xk9!')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vogueswear.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Session config — fixes cart stopping after first use
    app.config['SESSION_COOKIE_SECURE'] = False       # False for localhost (HTTP)
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours in seconds

    # Upload folder
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # 3. Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    # 4. Register blueprints
    from app.routes import main
    from app.admin_routes import admin_bp

    app.register_blueprint(main)
    app.register_blueprint(admin_bp)

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))