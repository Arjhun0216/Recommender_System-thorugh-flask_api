# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from config import config_map

db            = SQLAlchemy()
bcrypt        = Bcrypt()
login_manager = LoginManager()

login_manager.login_view    = "portal.login"
login_manager.login_message = "Please log in to access your dashboard."

# Get the root directory of the project
# app/__init__.py is inside app/ so we go one level up
ROOT_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR   = os.path.join(ROOT_DIR, "templates")
STATIC_DIR     = os.path.join(ROOT_DIR, "static")

def create_app(config_name="default"):
    app = Flask(
        __name__,
        template_folder = TEMPLATE_DIR,
        static_folder   = STATIC_DIR
    )

    app.config.from_object(config_map[config_name])

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    from app.routes import api
    app.register_blueprint(api, url_prefix="/api/v1")

    from app.portal import portal
    app.register_blueprint(portal)

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import Developer
    return Developer.query.get(int(user_id))