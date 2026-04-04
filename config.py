# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///recommendation.db"

class ProductionConfig(Config):
    DEBUG = False
    # Railway injects DATABASE_URL automatically
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///recommendation.db"
    ).replace("postgres://", "postgresql://")
    # ↑ Railway gives postgres:// but SQLAlchemy needs postgresql://
    # This one line fixes that automatically

config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}