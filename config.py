# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration — shared across all environments."""
    
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Silence a Flask-SQLAlchemy warning
    
class DevelopmentConfig(Config):
    """Settings for local development."""
    
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///recommendation.db"
    
class ProductionConfig(Config):
    """Settings for when you deploy to a server."""
    
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///recommendation.db")


# This dictionary lets us select config by name (used in __init__.py)
config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}