import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# 1. Initialize extensions OUTSIDE the function so they can be imported
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # 2. Configuration
    # Ensure this points to the correct database file inside your project
    app.config['SECRET_KEY'] = 'dev-key-vogues-123'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vogueswear.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Path for uploaded product images
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')

    # 3. Initialize extensions with the app instance
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Tell Flask-Login where the login page is
    login_manager.login_view = 'main.login' 

    # 4. REGISTER BLUEPRINTS
    # We use 'vogueswear' here because that is your folder name
    from app.routes import main
    from app.admin_routes import admin_bp
    
    app.register_blueprint(main)
    app.register_blueprint(admin_bp)

    return app

# This helps Flask-Login find the user in the database
@login_manager.user_loader
def load_user(user_id):
    from vogueswear.models import User
    return User.query.get(int(user_id))