import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'vogueswear-secret-2025'
    
    # Fix postgres:// -> postgresql:// for SQLAlchemy compatibility
    db_url = os.environ.get('DATABASE_URL') or 'sqlite:///vogueswear.db'
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = db_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    # Fix SSL connection issue on Render
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'sslmode': 'require'} if os.environ.get('DATABASE_URL') else {}
    }