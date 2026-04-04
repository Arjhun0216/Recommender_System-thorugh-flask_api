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
    # PythonAnywhere MySQL format:
    # mysql+pymysql://username:password@username.mysql.pythonanywhere-services.com/username$dbname
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///recommendation.db")

config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}