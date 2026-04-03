
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config_map

# Create the database object here — but don't attach it to an app yet
db = SQLAlchemy()

def create_app(config_name="default"):
    """
    App factory function.
    Creates a fresh Flask app, configures it, and registers all pieces.
    """
    
    app = Flask(__name__)
    
    # Load config (DevelopmentConfig by default)
    app.config.from_object(config_map[config_name])
    
    # Attach database to this app
    db.init_app(app)
    
    # Register routes (we'll build this file next)
    from app.routes import api
    app.register_blueprint(api, url_prefix="/api/v1")
    
    return app